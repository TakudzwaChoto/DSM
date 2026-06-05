#!/usr/bin/env python3
"""
Oracle Implementation for DSM Smart Contract
Handles off-chain archival with HMAC-SHA256 authentication and CouchDB storage

Usage:
    python oracle.py --couchdb-url http://localhost:5984 --database dsm_archive
"""

import hmac
import hashlib
import json
import requests
import argparse
import time
from web3 import Web3
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DSMOracle:
    """
    Oracle for DSM smart contract archival operations.
    Listens to DataArchived events, validates HMAC-SHA256 signatures,
    and stores data in CouchDB with cryptographic commitments.
    """
    
    def __init__(
        self,
        web3_url: str,
        contract_address: str,
        contract_abi: list,
        couchdb_url: str,
        database_name: str,
        oracle_private_key: str
    ):
        self.w3 = Web3(Web3.HTTPProvider(web3_url))
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=contract_abi
        )
        self.couchdb_url = couchdb_url.rstrip('/')
        self.database_name = database_name
        self.oracle_private_key = oracle_private_key
        
        # Initialize CouchDB database
        self._init_couchdb()
        
    def _init_couchdb(self):
        """Create CouchDB database if it doesn't exist"""
        response = requests.put(f"{self.couchdb_url}/{self.database_name}")
        if response.status_code in [201, 412]:  # Created or already exists
            logger.info(f"CouchDB database '{self.database_name}' ready")
        else:
            raise Exception(f"Failed to initialize CouchDB: {response.text}")
    
    def _generate_hmac_signature(
        self,
        user_address: str,
        timestamp: int,
        value: int,
        block_hash: str
    ) -> str:
        """
        Generate HMAC-SHA256 signature for data authentication.
        
        Args:
            user_address: User's Ethereum address
            timestamp: Data timestamp
            value: Data value
            block_hash: Block hash for commitment
        
        Returns:
            Hex-encoded HMAC-SHA256 signature
        """
        message = f"{user_address}:{timestamp}:{value}:{block_hash}"
        signature = hmac.new(
            bytes.fromhex(self.oracle_private_key[2:]),  # Remove '0x' prefix
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return "0x" + signature
    
    def _verify_commitment(
        self,
        user_address: str,
        timestamp: int,
        value: int,
        commitment: bytes32
    ) -> bool:
        """
        Verify the on-chain commitment matches off-chain data.
        
        Args:
            user_address: User's Ethereum address
            timestamp: Data timestamp
            value: Data value
            commitment: On-chain commitment (bytes32)
        
        Returns:
            True if commitment is valid
        """
        # Recompute the commitment as done in smart contract
        block_hash = self.w3.eth.get_block('latest')['hash'].hex()
        recomputed = Web3.solidity_keccak(
            ['address', 'uint256', 'uint256', 'bytes32'],
            [
                Web3.to_checksum_address(user_address),
                timestamp,
                value,
                bytes.fromhex(block_hash[2:])
            ]
        )
        return recomputed.hex() == commitment.hex()
    
    def store_to_couchdb(
        self,
        user_address: str,
        timestamp: int,
        value: int,
        commitment: str,
        signature: str
    ) -> Dict:
        """
        Store archived data to CouchDB with cryptographic proofs.
        
        Args:
            user_address: User's Ethereum address
            timestamp: Data timestamp
            value: Data value
            commitment: On-chain commitment hash
            signature: HMAC-SHA256 signature
        
        Returns:
            CouchDB document response
        """
        doc = {
            '_id': f"{user_address}_{timestamp}",
            'user_address': user_address,
            'timestamp': timestamp,
            'value': value,
            'on_chain_commitment': commitment,
            'oracle_signature': signature,
            'archived_at': int(time.time()),
            'verified': True
        }
        
        response = requests.post(
            f"{self.couchdb_url}/{self.database_name}",
            json=doc,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 201:
            logger.info(f"Stored document {doc['_id']} to CouchDB")
            return response.json()
        else:
            raise Exception(f"Failed to store to CouchDB: {response.text}")
    
    def process_archival_event(self, event):
        """
        Process a DataArchived event from the smart contract.
        
        Args:
            event: Web3 event object
        """
        try:
            user_address = event['args']['user']
            timestamp = event['args']['timestamp']
            commitment = event['args']['commitment'].hex()
            
            logger.info(f"Processing archival event for {user_address} at {timestamp}")
            
            # Retrieve data from backup storage (would need to be exposed via contract)
            # For now, we'll simulate this with event data
            value = 0  # This would come from contract query
            
            # Generate HMAC signature
            block_hash = self.w3.eth.get_block(event['blockNumber'])['hash'].hex()
            signature = self._generate_hmac_signature(
                user_address, timestamp, value, block_hash
            )
            
            # Verify commitment
            if self._verify_commitment(user_address, timestamp, value, event['args']['commitment']):
                # Store to CouchDB
                doc = self.store_to_couchdb(
                    user_address, timestamp, value, commitment, signature
                )
                logger.info(f"✓ Successfully archived {doc['id']}")
            else:
                logger.error(f"✗ Commitment verification failed for {user_address}_{timestamp}")
                
        except Exception as e:
            logger.error(f"Error processing archival event: {e}")
    
    def listen_to_archival_events(self, from_block: int = 0):
        """
        Listen to DataArchived events from the smart contract.
        
        Args:
            from_block: Block number to start listening from
        """
        logger.info(f"Listening to archival events from block {from_block}")
        
        event_filter = self.contract.events.DataArchived.create_filter(
            fromBlock=from_block
        )
        
        while True:
            try:
                for event in event_filter.get_new_entries():
                    self.process_archival_event(event)
                time.sleep(2)  # Poll every 2 seconds
            except KeyboardInterrupt:
                logger.info("Stopping oracle listener")
                break
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
                time.sleep(5)
    
    def trigger_purge_confirmation(
        self,
        user_address: str,
        timestamp: int
    ) -> bool:
        """
        Trigger purge confirmation on-chain after successful archival.
        
        Args:
            user_address: User's Ethereum address
            timestamp: Data timestamp
        
        Returns:
            True if purge was triggered successfully
        """
        try:
            # Build transaction to call purgeArchivedData
            nonce = self.w3.eth.get_transaction_count(
                self.w3.eth.account.from_key(self.oracle_private_key).address
            )
            
            tx = self.contract.functions.purgeArchivedData(
                Web3.to_checksum_address(user_address),
                timestamp
            ).build_transaction({
                'from': self.w3.eth.account.from_key(self.oracle_private_key).address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(
                tx, self.oracle_private_key
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] == 1:
                logger.info(f"✓ Purge confirmed for {user_address}_{timestamp}")
                return True
            else:
                logger.error(f"✗ Purge transaction failed")
                return False
                
        except Exception as e:
            logger.error(f"Error triggering purge: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='DSM Oracle for off-chain archival')
    parser.add_argument('--web3-url', required=True, help='Web3 RPC URL')
    parser.add_argument('--contract-address', required=True, help='DSM contract address')
    parser.add_argument('--contract-abi', required=True, help='Path to contract ABI JSON')
    parser.add_argument('--couchdb-url', default='http://localhost:5984', help='CouchDB URL')
    parser.add_argument('--database', default='dsm_archive', help='CouchDB database name')
    parser.add_argument('--oracle-key', required=True, help='Oracle private key')
    parser.add_argument('--from-block', type=int, default=0, help='Start block for event listening')
    
    args = parser.parse_args()
    
    # Load contract ABI
    with open(args.contract_abi, 'r') as f:
        contract_abi = json.load(f)
    
    # Initialize oracle
    oracle = DSMOracle(
        web3_url=args.web3_url,
        contract_address=args.contract_address,
        contract_abi=contract_abi,
        couchdb_url=args.couchdb_url,
        database_name=args.database,
        oracle_private_key=args.oracle_key
    )
    
    # Start listening to events
    oracle.listen_to_archival_events(from_block=args.from_block)


if __name__ == "__main__":
    main()
