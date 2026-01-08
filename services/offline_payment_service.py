"""
Offline Payment Service - Create orders locally when server is offline

Orders are stored locally and synced to server when connection is available.
VietQR URL is generated directly without server.
"""

import json
import uuid
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

from core.config import BANK_INFO, PACKAGE_PRICES


class OfflinePaymentService:
    """Handle payments when server is offline"""
    
    def __init__(self):
        # Store orders in AppData
        import os
        app_data = os.getenv('LOCALAPPDATA', '.')
        self.orders_dir = Path(app_data) / "FourT"
        self.orders_dir.mkdir(parents=True, exist_ok=True)
        self.orders_file = self.orders_dir / "pending_orders.json"
        self.pending_orders: Dict[str, dict] = {}
        self._load_orders()
    
    def _load_orders(self):
        """Load pending orders from disk"""
        try:
            if self.orders_file.exists():
                with open(self.orders_file, 'r', encoding='utf-8') as f:
                    self.pending_orders = json.load(f)
        except Exception as e:
            print(f"[OfflinePayment] Error loading orders: {e}")
            self.pending_orders = {}
    
    def _save_orders(self):
        """Save pending orders to disk"""
        try:
            with open(self.orders_file, 'w', encoding='utf-8') as f:
                json.dump(self.pending_orders, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[OfflinePayment] Error saving orders: {e}")
    
    def create_offline_order(self, package: str, amount: int = 0) -> Optional[Dict]:
        """
        Create order locally (no server needed)
        
        Args:
            package: Package type (basic, pro, premium)
            amount: Amount from server config (0 = use local fallback)
            
        Returns:
            Order data with QR URL or None if failed
        """
        try:
            # Use provided amount or fallback to local config
            if amount > 0:
                final_amount = amount
            elif package in PACKAGE_PRICES:
                final_amount = PACKAGE_PRICES[package]
            else:
                print(f"[OfflinePayment] Invalid package: {package}")
                return None
            order_id = str(uuid.uuid4())[:8].upper()
            content = f"FOURT {order_id}"
            
            # Generate VietQR URL directly (no server needed!)
            bank_id = BANK_INFO.get("BANK_ID", "")
            account_no = BANK_INFO.get("ACCOUNT_NO", "")
            template = BANK_INFO.get("TEMPLATE", "compact2")
            account_name = urllib.parse.quote(BANK_INFO.get("ACCOUNT_NAME", ""))
            add_info = urllib.parse.quote(content)
            
            if not bank_id or not account_no:
                print("[OfflinePayment] Missing bank info")
                return None
            
            qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-{template}.png?amount={final_amount}&addInfo={add_info}&accountName={account_name}"
            
            # Save order locally
            order_data = {
                "order_id": order_id,
                "package": package,
                "amount": final_amount,
                "content": content,
                "qr_url": qr_url,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "created_offline": True,
                "synced_to_server": False,
                "bank_info": {
                    "bank_id": bank_id,
                    "account_no": account_no,
                    "account_name": BANK_INFO.get("ACCOUNT_NAME", "")
                }
            }
            
            self.pending_orders[order_id] = order_data
            self._save_orders()
            
            print(f"[OfflinePayment] Created offline order: {order_id}")
            return order_data
            
        except Exception as e:
            print(f"[OfflinePayment] Error creating order: {e}")
            return None
    
    def get_pending_orders(self) -> List[Dict]:
        """Get all pending (unsynced) orders"""
        return [o for o in self.pending_orders.values() if not o.get("synced_to_server")]
    
    def mark_order_synced(self, order_id: str):
        """Mark order as synced to server"""
        if order_id in self.pending_orders:
            self.pending_orders[order_id]["synced_to_server"] = True
            self._save_orders()
    
    def sync_orders_to_server(self) -> int:
        """
        Sync pending orders to server when online
        
        Returns:
            Number of orders synced
        """
        from services.connection_manager import is_server_offline
        
        if is_server_offline():
            print("[OfflinePayment] Cannot sync - server offline")
            return 0
        
        synced_count = 0
        pending = self.get_pending_orders()
        
        if not pending:
            return 0
        
        try:
            import requests
            from core.config import get_license_server_url
            
            base_url = get_license_server_url()
            
            for order in pending:
                try:
                    # Send order to server
                    url = f"{base_url}/payment/sync-offline-order"
                    print(f"[OfflinePayment] Syncing to: {url}")
                    response = requests.post(
                        url,
                        json=order,
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        self.mark_order_synced(order["order_id"])
                        synced_count += 1
                        print(f"[OfflinePayment] Synced order: {order['order_id']}")
                    else:
                        print(f"[OfflinePayment] Sync failed for {order['order_id']}: {response.status_code}")
                        
                except Exception as e:
                    print(f"[OfflinePayment] Error syncing {order['order_id']}: {e}")
                    
        except Exception as e:
            print(f"[OfflinePayment] Sync error: {e}")
        
        return synced_count


# Singleton
_offline_payment_service = None

def get_offline_payment_service() -> OfflinePaymentService:
    global _offline_payment_service
    if _offline_payment_service is None:
        _offline_payment_service = OfflinePaymentService()
    return _offline_payment_service
