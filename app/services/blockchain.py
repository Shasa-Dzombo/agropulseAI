from web3 import Web3
from eth_account import Account
from typing import Optional
import json
from app.config import settings
from datetime import datetime, timedelta


class BlockchainService:
    # Smart Contract ABI (simplified version)
    contract_abi = [
        {
            "inputs": [
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "string", "name": "permitType", "type": "string"}
            ],
            "name": "mintPermit",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
            "name": "usePermit",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
            "name": "isPermitValid",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]

    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_RPC_URL))
        self.contract_address = settings.PERMIT_CONTRACT_ADDRESS
        self._account: Optional[Account] = None
        self._contract = None

    @property
    def account(self) -> Account:
        """Lazily parse the wallet key so a placeholder PRIVATE_KEY doesn't
        crash the app at import time - it only fails when a blockchain
        operation is actually attempted."""
        if self._account is None:
            try:
                self._account = Account.from_key(settings.PRIVATE_KEY)
            except (ValueError, Exception) as e:
                raise RuntimeError(
                    "Blockchain wallet not configured: PRIVATE_KEY is missing or invalid. "
                    "Set a real private key in the environment to use blockchain features."
                ) from e
        return self._account

    @property
    def contract(self):
        """Lazily build the contract binding for the same reason as `account`."""
        if self._contract is None:
            try:
                checksum_address = Web3.to_checksum_address(self.contract_address)
            except ValueError as e:
                raise RuntimeError(
                    "Blockchain contract not configured: PERMIT_CONTRACT_ADDRESS is missing "
                    "or invalid. Set a real deployed contract address to use blockchain features."
                ) from e
            self._contract = self.w3.eth.contract(address=checksum_address, abi=self.contract_abi)
        return self._contract
    
    async def mint_permit(self, wallet_address: str, permit_type: str = "diagnosis") -> dict:
        """
        Mint a new permit NFT for the user
        """
        try:
            # Prepare transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            transaction = self.contract.functions.mintPermit(
                Web3.to_checksum_address(wallet_address),
                permit_type
            ).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': settings.GAS_LIMIT,
                'gasPrice': self.w3.eth.gas_price,
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Extract token ID from logs
            token_id = None
            if receipt.logs:
                # Parse the Transfer event to get token ID
                token_id = receipt.logs[0]['topics'][3].hex()
            
            return {
                "success": True,
                "transaction_hash": receipt.transactionHash.hex(),
                "token_id": token_id,
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def verify_permit(self, token_id: str) -> bool:
        """
        Verify if a permit is valid and unused
        """
        try:
            is_valid = self.contract.functions.isPermitValid(int(token_id, 16)).call()
            return is_valid
        except Exception as e:
            print(f"Error verifying permit: {e}")
            return False
    
    async def use_permit(self, token_id: str) -> dict:
        """
        Mark a permit as used on the blockchain
        """
        try:
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            transaction = self.contract.functions.usePermit(
                int(token_id, 16)
            ).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': settings.GAS_LIMIT,
                'gasPrice': self.w3.eth.gas_price,
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                "success": True,
                "transaction_hash": receipt.transactionHash.hex(),
                "block_number": receipt.blockNumber
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_permit_details(self, token_id: str) -> Optional[dict]:
        """
        Get detailed information about a permit
        """
        try:
            # This would call view functions on the smart contract
            # to retrieve permit metadata
            return {
                "token_id": token_id,
                "is_valid": await self.verify_permit(token_id),
                "contract_address": self.contract_address
            }
        except Exception as e:
            print(f"Error getting permit details: {e}")
            return None


# Singleton instance
blockchain_service = BlockchainService()
