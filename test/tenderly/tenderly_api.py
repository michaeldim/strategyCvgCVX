#!/usr/bin/env python3
"""
Tenderly API Client for Strategy Testing

This module provides a comprehensive client for testing strategies
using Tenderly Virtual TestNets (VNets). It includes functionality for:
- Creating and managing Virtual TestNets
- Deploying and testing strategies
- Simulating transactions and monitoring results
- Managing snapshots and time manipulation

API Documentation:
- https://docs.tenderly.co/reference/api#/operations/getVnet
- https://docs.tenderly.co/virtual-testnets/quickstart
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from web3 import Web3
from eth_account import Account

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("strategy-tenderly")


class TenderlyVNetClient:
    """
    Tenderly Virtual TestNet client for strategy testing
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the Tenderly client
        
        Args:
            verbose: Enable detailed logging
        """
        # Load environment variables
        load_dotenv()
        
        # Get credentials
        self.access_key = os.getenv("TENDERLY_ACCESS_KEY")
        self.account_id = os.getenv("TENDERLY_ACCOUNT_ID")
        self.project_id = os.getenv("TENDERLY_PROJECT_ID")
        self.verbose = verbose
        
        # Validate credentials
        if not all([self.access_key, self.account_id, self.project_id]):
            raise ValueError(
                "Missing Tenderly credentials. Please set:\n"
                "  TENDERLY_ACCESS_KEY\n"
                "  TENDERLY_ACCOUNT_ID\n"
                "  TENDERLY_PROJECT_ID"
            )
        
        # API configuration
        self.base_url = "https://api.tenderly.co/api/v1"
        self.headers = {
            "X-Access-Key": self.access_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # VNet state
        self.vnet_id = None
        self.rpc_url = None
        self.admin_rpc_url = None
        self.chain_id = None
        self.w3 = None
        self.admin_w3 = None
        
        if self.verbose:
            logger.info(f"Initialized Tenderly client for {self.account_id}/{self.project_id}")
    
    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make an API request to Tenderly
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request payload
            
        Returns:
            Response data or None if failed
        """
        url = f"{self.base_url}{endpoint}"
        
        if self.verbose:
            logger.info(f"API Request: {method} {url}")
            if data:
                logger.debug(f"Payload: {json.dumps(data, indent=2)}")
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code >= 200 and response.status_code < 300:
                return response.json() if response.text else {}
            else:
                logger.error(f"API Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def create_vnet(self,
                   display_name: str = "Strategy Test",
                   network_id: str = "1",
                   block_number: Optional[int] = None,
                   chain_id: Optional[int] = None) -> bool:
        """
        Create a new Virtual TestNet
        
        Args:
            display_name: Human-readable name
            network_id: Network to fork (1 = Ethereum mainnet)
            block_number: Block to fork from (None = latest)
            chain_id: Custom chain ID (None = use network default)
            
        Returns:
            True if successful
        """
        # Generate a unique slug for the VNet
        import time
        import random
        timestamp = int(time.time())
        random_suffix = random.randint(1000, 9999)
        slug = f"strategy-vnet-{timestamp}-{random_suffix}"
        
        # Prepare payload according to Tenderly API documentation
        payload = {
            "slug": slug,
            "display_name": display_name,
            "fork_config": {
                "network_id": int(network_id),
                "block_number": block_number if block_number else "latest"
            },
            "virtual_network_config": {
                "chain_config": {
                    "chain_id": chain_id if chain_id else (73571 + random_suffix)
                }
            },
            "sync_state_config": {
                "enabled": False,
                "commitment_level": "latest"
            },
            "explorer_page_config": {
                "enabled": True,
                "verification_visibility": "bytecode"
            }
        }
        
        # Create VNet
        endpoint = f"/account/{self.account_id}/project/{self.project_id}/vnets"
        result = self.make_request("POST", endpoint, payload)
        
        if not result:
            logger.error("Failed to create Virtual TestNet")
            return False
        
        # Extract VNet details
        self.vnet_id = result.get("id")
        self.chain_id = result.get("virtual_network_config", {}).get("chain_config", {}).get("chain_id", 1)
        
        # Extract RPC URLs from the response
        rpcs = result.get("rpcs", [])
        for rpc in rpcs:
            if rpc.get("name") == "Admin RPC":
                self.admin_rpc_url = rpc.get("url")
            elif rpc.get("name") == "Public RPC":
                self.rpc_url = rpc.get("url")
        
        # Fallback to constructed URLs if not in response
        if not self.rpc_url:
            self.rpc_url = self.get_rpc_url()
        if not self.admin_rpc_url:
            self.admin_rpc_url = self.get_rpc_url(admin=True)
        
        # Initialize Web3 connections
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.admin_w3 = Web3(Web3.HTTPProvider(self.admin_rpc_url))
        
        logger.info(f"✅ Created VNet: {self.vnet_id}")
        logger.info(f"   RPC URL: {self.rpc_url}")
        logger.info(f"   Admin RPC: {self.admin_rpc_url}")
        logger.info(f"   Dashboard: {self.get_dashboard_url()}")
        
        return True
    
    def get_rpc_url(self, vnet_id: Optional[str] = None, admin: bool = False) -> str:
        """
        Get the RPC URL for a Virtual TestNet
        
        Args:
            vnet_id: VNet ID (None = use current)
            admin: Get admin RPC URL
            
        Returns:
            RPC URL
        """
        vnet_id = vnet_id or self.vnet_id
        if not vnet_id:
            raise ValueError("No VNet ID available")
        
        base = f"https://virtual.mainnet.rpc.tenderly.co/{vnet_id}"
        if admin:
            # Admin RPC has special privileges for state manipulation
            return f"{base}?type=admin"
        return base
    
    def get_dashboard_url(self, vnet_id: Optional[str] = None) -> str:
        """Get the dashboard URL for viewing the VNet"""
        vnet_id = vnet_id or self.vnet_id
        return f"https://dashboard.tenderly.co/{self.account_id}/{self.project_id}/virtualnet/{vnet_id}"
    
    def fund_account(self, address: str, amount_eth: float = 100) -> bool:
        """
        Fund an account with ETH
        
        Args:
            address: Address to fund
            amount_eth: Amount in ETH
            
        Returns:
            True if successful
        """
        if not self.admin_w3:
            logger.error("No admin Web3 connection")
            return False
        
        # Use Tenderly's eth_sendTransaction with admin privileges
        amount_wei = Web3.to_wei(amount_eth, 'ether')
        
        try:
            # Set balance using Tenderly's state override
            result = self.admin_w3.provider.make_request(
                "tenderly_setBalance",
                [address, hex(amount_wei)]
            )
            
            if self.verbose:
                logger.info(f"Funded {address} with {amount_eth} ETH")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fund account: {e}")
            return False
    
    def set_erc20_balance(self, token_address: str, wallet_address: str, amount: int) -> bool:
        """
        Set ERC20 token balance for an account
        
        Args:
            token_address: ERC20 token contract
            wallet_address: Wallet to fund
            amount: Amount in token units
            
        Returns:
            True if successful
        """
        if not self.admin_w3:
            logger.error("No admin Web3 connection")
            return False
        
        try:
            # Use Tenderly's state override to set storage
            # Standard ERC20 balance mapping is usually at slot 0
            result = self.admin_w3.provider.make_request(
                "tenderly_setErc20Balance",
                [token_address, wallet_address, hex(amount)]
            )
            
            if self.verbose:
                logger.info(f"Set balance of {token_address} for {wallet_address} to {amount}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set ERC20 balance: {e}")
            return False
    
    def take_snapshot(self) -> Optional[str]:
        """
        Take a snapshot of the current VNet state
        
        Returns:
            Snapshot ID or None if failed
        """
        if not self.vnet_id:
            logger.error("No VNet active")
            return None
        
        endpoint = f"/account/{self.account_id}/project/{self.project_id}/vnets/{self.vnet_id}/snapshots"
        result = self.make_request("POST", endpoint)
        
        if result:
            snapshot_id = result.get("id")
            logger.info(f"📸 Snapshot created: {snapshot_id}")
            return snapshot_id
        
        return None
    
    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        Restore VNet to a previous snapshot
        
        Args:
            snapshot_id: Snapshot to restore
            
        Returns:
            True if successful
        """
        if not self.vnet_id:
            logger.error("No VNet active")
            return False
        
        endpoint = f"/account/{self.account_id}/project/{self.project_id}/vnets/{self.vnet_id}/snapshots/{snapshot_id}/revert"
        result = self.make_request("POST", endpoint)
        
        if result:
            logger.info(f"♻️ Restored snapshot: {snapshot_id}")
            return True
        
        return False
    
    def increase_time(self, seconds: int) -> bool:
        """
        Increase blockchain time
        
        Args:
            seconds: Seconds to advance
            
        Returns:
            True if successful
        """
        if not self.admin_w3:
            logger.error("No admin Web3 connection")
            return False
        
        try:
            result = self.admin_w3.provider.make_request(
                "evm_increaseTime",
                [seconds]
            )
            
            # Mine a block to apply the time change
            self.mine_block()
            
            if self.verbose:
                logger.info(f"⏰ Advanced time by {seconds} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to increase time: {e}")
            return False
    
    def mine_block(self) -> bool:
        """
        Force mine a new block
        
        Returns:
            True if successful
        """
        if not self.admin_w3:
            logger.error("No admin Web3 connection")
            return False
        
        try:
            result = self.admin_w3.provider.make_request("evm_mine", [])
            
            if self.verbose:
                logger.info("⛏️ Mined new block")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to mine block: {e}")
            return False
    
    def delete_vnet(self, vnet_id: Optional[str] = None) -> bool:
        """
        Delete a Virtual TestNet
        
        Args:
            vnet_id: VNet to delete (None = current)
            
        Returns:
            True if successful
        """
        vnet_id = vnet_id or self.vnet_id
        if not vnet_id:
            logger.error("No VNet ID provided")
            return False
        
        endpoint = f"/account/{self.account_id}/project/{self.project_id}/vnets/{vnet_id}"
        result = self.make_request("DELETE", endpoint)
        
        if result is not None:
            logger.info(f"🗑️ Deleted VNet: {vnet_id}")
            
            # Clear state if it was the current VNet
            if vnet_id == self.vnet_id:
                self.vnet_id = None
                self.rpc_url = None
                self.admin_rpc_url = None
                self.w3 = None
                self.admin_w3 = None
            
            return True
        
        return False
    
    def get_vnet_info(self) -> Dict[str, Any]:
        """
        Get current VNet information
        
        Returns:
            Dict with VNet details
        """
        return {
            "vnet_id": self.vnet_id,
            "rpc_url": self.rpc_url,
            "admin_rpc_url": self.admin_rpc_url,
            "chain_id": self.chain_id,
            "dashboard_url": self.get_dashboard_url() if self.vnet_id else None,
            "account_id": self.account_id,
            "project_id": self.project_id
        }
    
    def save_vnet_info(self, filename: str = "vnet_info.json") -> None:
        """Save VNet info to file"""
        info = self.get_vnet_info()
        info["created_at"] = datetime.now().isoformat()
        
        with open(filename, "w") as f:
            json.dump(info, f, indent=2)
        
        logger.info(f"💾 VNet info saved to {filename}")


def main():
    """Example usage of the Tenderly VNet client"""

    # Create client
    client = TenderlyVNetClient(verbose=True)

    # Create a VNet
    if client.create_vnet(
        display_name="Strategy Test",
        network_id="1",  # Ethereum mainnet
        block_number=None,  # Latest block
        chain_id=31337  # Custom chain ID for testing
    ):
        # Save VNet info
        client.save_vnet_info()
        
        # Fund a test account
        test_account = "0x742d35Cc6634C0532925a3b844Bc9e7595f0fA42"
        client.fund_account(test_account, 1000)
        
        # Take a snapshot
        snapshot_id = client.take_snapshot()
        
        # Advance time by 1 day
        client.increase_time(86400)
        
        # Restore snapshot if needed
        # client.restore_snapshot(snapshot_id)
        
        print(f"\n✅ VNet ready for testing!")
        print(f"   RPC URL: {client.rpc_url}")
        print(f"   Dashboard: {client.get_dashboard_url()}")


if __name__ == "__main__":
    main()