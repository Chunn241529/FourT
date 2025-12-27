"""
Sepay Webhook Router
Handles automatic payment verification from Sepay.vn
"""

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import logging
import json
import re

from core.config import SEPAY_API_KEY, SEPAY_ENABLED, LICENSE_DURATION_DAYS
from backend import database as db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sepay",
    tags=["sepay"]
)


class SepayWebhookData(BaseModel):
    """Sepay webhook payload structure"""
    id: int
    gateway: str  # Bank code (MB, VCB, etc.)
    transaction_date: str
    account_number: str
    sub_account: Optional[str] = None
    amount_in: int  # Tiền vào
    amount_out: int  # Tiền ra
    accumulated: int  # Số dư
    code: Optional[str] = None  # Transaction code
    transaction_content: str  # Nội dung giao dịch
    reference_number: str  # Mã tham chiếu
    body: Optional[str] = None


def verify_api_key(api_key: Optional[str]) -> bool:
    """Verify webhook is from Sepay"""
    if not SEPAY_ENABLED:
        logger.warning("Sepay is not enabled - missing API credentials")
        return False
    
    if not api_key:
        logger.warning("No API key provided in request")
        return False
    
    is_valid = api_key == SEPAY_API_KEY
    if not is_valid:
        logger.warning(f"Invalid API key: {api_key[:10]}...")
    
    return is_valid


def extract_order_id(content: str) -> Optional[str]:
    """
    Extract order ID from payment description
    Expected format: "FOURT ABC123" but flexible with spacing/punctuation
    """
    if not content:
        return None
    
    content = content.upper()
    
    # Try to find pattern: FOURT followed by 8 alphanumeric characters
    # This regex is flexible with spaces, punctuation between FOURT and the ID
    match = re.search(r'FOURT[\s\-:]*([A-Z0-9]{8})', content)
    if match:
        return match.group(1)
    
    return None


@router.post("/webhook")
async def sepay_webhook(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Receive webhook from Sepay when payment is made
    
    Sepay sends webhook when money arrives in bank account
    We verify and auto-activate license
    """
    
    # Log raw request body for debugging
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
        logger.info(f"[Sepay Webhook] Raw body: {body_str}")
        
        # Parse JSON manually to handle any field issues
        data_dict = json.loads(body_str)
        logger.info(f"[Sepay Webhook] Parsed data keys: {list(data_dict.keys())}")
        
        # Convert to dict (already done above)
        data = data_dict
        
    except Exception as e:
        logger.error(f"[Sepay Webhook] Error parsing request: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid request format: {str(e)}")
    
    # Log incoming webhook
    # Handle different field names (camelCase vs snake_case)
    amount_in = data.get("amount_in") or data.get("amountIn") or data.get("transferAmount") or 0
    content = data.get("transaction_content") or data.get("content") or data.get("description") or ""
    reference_number = data.get("reference_number") or data.get("referenceCode") or data.get("id")
    gateway = data.get("gateway") or "Unknown"
    transaction_date = data.get("transaction_date") or data.get("transactionDate") or str(datetime.now())
    
    logger.info(f"[Sepay Webhook] Processed: Amount={amount_in}, Content={content}")
    
    # Extract API key from Authorization header
    # Sepay sends: "Apikey API_KEY" or "Bearer API_KEY"
    api_key = None
    if authorization:
        if authorization.startswith("Apikey "):
            api_key = authorization[7:]  # Remove "Apikey " prefix
        elif authorization.startswith("Bearer "):
            api_key = authorization[7:]  # Remove "Bearer " prefix
        else:
            # Try to use the whole value as API key
            api_key = authorization
    
    logger.info(f"[Sepay Webhook] Authorization header: {authorization[:20] if authorization else 'None'}...")
    
    # Verify API key
    if not verify_api_key(api_key):
        logger.error("[Sepay Webhook] Invalid API key - rejecting request")
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Only process incoming money (amount_in > 0)
    try:
        amount_in = int(amount_in)
    except:
        amount_in = 0
        
    if amount_in <= 0:
        logger.info(f"[Sepay Webhook] Skipping - no incoming money (amount_in={amount_in})")
        return {"message": "No incoming transaction", "success": True}
    
    # Extract order ID from transaction content
    order_id = extract_order_id(content)
    if not order_id:
        logger.warning(f"[Sepay Webhook] Could not extract order ID from: {content}")
        return {"error": "Invalid payment description format", "success": False}
    
    logger.info(f"[Sepay Webhook] Extracted order ID: {order_id}")
    
    # Find order from database
    order = await db.get_order(order_id)
    if not order:
        logger.warning(f"[Sepay Webhook] Order not found: {order_id}")
        return {"error": "Order not found", "success": False}
    
    # Check if already processed
    if order.get("payment_verified"):
        logger.info(f"[Sepay Webhook] Order already processed: {order_id}")
        return {"message": "Payment already processed", "success": True}
    
    # Verify amount matches
    if order["amount"] != amount_in:
        logger.error(f"[Sepay Webhook] Amount mismatch - Expected: {order['amount']}, Got: {amount_in}")
        return {"error": "Amount mismatch", "success": False}
    
    logger.info(f"[Sepay Webhook] Amount verified: {amount_in} VND")
    
    # Generate license key
    license_key = f"LICENSE-{order['package'].upper()}-{order_id}"
    package = order["package"]
    
    # Create license data
    license_data = {
        "license_key": license_key,
        "package": package,
        "device_id": None,  # Will be set when client activates
        "ipv4": None,  # Will be set when client activates
        "activated_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=LICENSE_DURATION_DAYS)).isoformat(),
        "user_id": None,  # Will be set to device_id when client activates
        "transaction_id": str(reference_number),
        "transaction_date": str(transaction_date),
        "gateway": gateway
    }
    
    # Store license in database
    await db.create_license(license_data)
    
    # Update order status
    await db.update_order(order_id, {
        "payment_verified": True,
        "transaction_id": str(reference_number),
        "verified_at": datetime.now().isoformat(),
        "license_key": license_key,
        "status": "completed",
        "gateway": gateway
    })
    
    logger.info(f"[Sepay Webhook] ✅ License activated successfully: {license_key} for package {package}")
    logger.info(f"[Sepay Webhook] Transaction via {gateway} bank")
    
    return {
        "success": True,
        "message": "Payment verified and license activated",
        "order_id": order_id,
        "license_key": license_key,
        "package": package
    }


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "sepay_enabled": SEPAY_ENABLED,
        "message": "Sepay webhook endpoint is ready" if SEPAY_ENABLED else "Sepay not configured"
    }
