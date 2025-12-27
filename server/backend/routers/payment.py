from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timedelta
import urllib.parse

from core.config import BANK_INFO, PACKAGE_PRICES, Packages, LICENSE_DURATION_DAYS
from backend import database as db

router = APIRouter(
    prefix="/payment",
    tags=["payment"]
)

class PaymentCreateRequest(BaseModel):
    package: str
    user_id: Optional[str] = None

class PaymentResponse(BaseModel):
    order_id: str
    amount: int
    content: str
    qr_url: str
    bank_info: dict

@router.post("/create", response_model=PaymentResponse)
async def create_payment(request: PaymentCreateRequest):
    """Create a payment order and return VietQR URL"""
    
    # Validate package
    if request.package not in PACKAGE_PRICES:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    amount = PACKAGE_PRICES[request.package]
    order_id = str(uuid.uuid4())[:8].upper() # Short ID for easier typing
    content = f"FOURT {order_id}"
    
    # Generate VietQR URL (QuickLink)
    # Format: https://img.vietqr.io/image/<BANK_ID>-<ACCOUNT_NO>-<TEMPLATE>.png?amount=<AMOUNT>&addInfo=<CONTENT>&accountName=<NAME>
    
    bank_id = BANK_INFO["BANK_ID"]
    account_no = BANK_INFO["ACCOUNT_NO"]
    template = BANK_INFO["TEMPLATE"]
    account_name = urllib.parse.quote(BANK_INFO["ACCOUNT_NAME"])
    add_info = urllib.parse.quote(content)
    
    qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-{template}.png?amount={amount}&addInfo={add_info}&accountName={account_name}"
    
    # Save order to database
    order_data = {
        "order_id": order_id,
        "package": request.package,
        "amount": amount,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "user_id": request.user_id
    }
    await db.create_order(order_data)
    
    return PaymentResponse(
        order_id=order_id,
        amount=amount,
        content=content,
        qr_url=qr_url,
        bank_info={
            "bank_id": bank_id,
            "account_no": account_no,
            "account_name": BANK_INFO["ACCOUNT_NAME"]
        }
    )

@router.get("/check/{order_id}")
async def check_payment_status(order_id: str):
    """Check payment status"""
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {"status": order["status"]}

@router.post("/mock-success/{order_id}")
async def mock_payment_success(order_id: str):
    """Mock successful payment (for testing)"""
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Generate a license key
    license_key = f"LICENSE-{order['package'].upper()}-{order_id}"
    package = order['package']
    
    # Create license data
    license_data = {
        "license_key": license_key,
        "package": package,
        "device_id": None,  # Will be set on activation
        "ipv4": None,  # Will be set on activation
        "activated_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=LICENSE_DURATION_DAYS)).isoformat(),
        "user_id": None  # Will be set to device_id on activation
    }
    
    # Store in database
    await db.create_license(license_data)
    
    # Update order status
    await db.update_order(order_id, {
        "status": "completed",
        "payment_verified": True,
        "license_key": license_key
    })
    
    return {
        "success": True,
        "status": "completed",
        "license_key": license_key,
        "package": package
    }


@router.get("/status/{order_id}")
async def get_payment_status(order_id: str):
    """
    Check payment status for an order
    Used by client to poll for payment verification from Casso
    """
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "order_id": order_id,
        "status": order.get("status", "pending"),
        "payment_verified": order.get("payment_verified", False),
        "license_key": order.get("license_key"),
        "package": order.get("package"),
        "amount": order.get("amount"),
        "verified_at": order.get("verified_at"),
        "transaction_id": order.get("transaction_id")
    }


@router.post("/sync-offline-order")
async def sync_offline_order(order_data: dict):
    """
    Receive an order that was created offline on client
    Store it in server database for Sepay webhook processing
    """
    order_id = order_data.get("order_id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Missing order_id")
    
    # Check if order already exists
    existing_order = await db.get_order(order_id)
    if existing_order:
        return {"success": True, "message": "Order already exists", "order_id": order_id}
    
    # Store the order
    new_order = {
        "order_id": order_id,
        "package": order_data.get("package"),
        "amount": order_data.get("amount"),
        "status": order_data.get("status", "pending"),
        "created_at": order_data.get("created_at"),
        "created_offline": True,
        "synced_at": datetime.now().isoformat(),
        "user_id": None
    }
    await db.create_order(new_order)
    
    print(f"[Payment] Synced offline order: {order_id}")
    
    return {"success": True, "message": "Order synced", "order_id": order_id}
