// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

/**
 * @title Dynamic Storage Management (DSM)
 * @notice A lifecycle-aware storage architecture for gas-efficient time-series smart contracts
 * @dev Implements timestamp-keyed mappings with copy-based two-stage migration
 */
contract DSM {
    // ============ State Variables ============
    
    /// @dev Active storage (Onchain A) - O(1) write access
    mapping(address => mapping(uint32 => uint96)) private _activeStorage;
    
    /// @dev Backup storage (Onchain B) - for migration window
    mapping(address => mapping(uint32 => uint96)) private _backupStorage;
    
    /// @dev Timestamp index for ordered iteration
    mapping(address => uint32[]) private _timestamps;
    
    /// @dev Essential events for off-chain oracles (4 events)
    event DataStored(address indexed user, uint32 timestamp, uint96 value);
    event MigrationCompleted(address indexed user, uint32 recordCount);
    event DataArchived(address indexed user, uint32 timestamp, bytes32 commitment);
    event PurgeCompleted(address indexed user, uint32 timestamp);
    
    // ============ Core Operations ============
    
    /**
     * @notice Store a data record (Ingress transition: S_Active)
     * @dev O(1) write complexity - no element shifting
     * @param value The data value to store
     */
    function storeData(uint96 value) public {
        unchecked {
            uint32 timestamp = uint32(block.timestamp);
            _activeStorage[msg.sender][timestamp] = value;
            _timestamps[msg.sender].push(timestamp);
            emit DataStored(msg.sender, timestamp, value);
        }
    }
    
    /**
     * @notice Batch store multiple records
     * @dev Useful for simulation and batch imports
     * @param values Array of values to store
     */
    function batchStoreData(uint96[] calldata values) public {
        unchecked {
            uint256 len = values.length;
            for (uint256 i = 0; i < len; i++) {
                uint32 offset = uint32((len - i) * 1 seconds);
                uint32 timestamp = uint32(block.timestamp) >= offset ? uint32(block.timestamp) - offset : 0;
                _activeStorage[msg.sender][timestamp] = values[i];
                _timestamps[msg.sender].push(timestamp);
                // No event emission for batch operations to reduce gas and output
            }
        }
    }
    
    /**
     * @notice Migrate data from active to backup storage (Migration transition: S_Active -> S_Backup)
     * @dev O(n) single linear pass - no quadratic complexity
     * @param user The user address whose data to migrate
     */
    function migrateData(address user) public {
        uint32[] storage userTimestamps = _timestamps[user];
        require(userTimestamps.length >= 1000, "DSM: Threshold not met");
        
        unchecked {
            uint32 cutoff = uint32(block.timestamp) >= 30 days ? uint32(block.timestamp) - 30 days : 0;
            uint32 migratedCount = 0;
            uint256 len = userTimestamps.length;
            
            for (uint256 i = 0; i < len; i++) {
                uint32 ts = userTimestamps[i];
                if (ts < cutoff) {
                    // Copy to backup storage (core innovation)
                    _backupStorage[user][ts] = _activeStorage[user][ts];
                    // Clear active storage
                    delete _activeStorage[user][ts];
                    migratedCount++;
                }
            }
            
            emit MigrationCompleted(user, migratedCount);
        }
    }
    
    /**
     * @notice Trigger off-chain archival via oracle (Archival transition: S_Backup -> S_Archived)
     * @dev Emits event for oracle to pick up, includes hash commitment
     * @param user The user address
     * @param timestamp The timestamp of the record to archive
     */
    function requestArchival(address user, uint32 timestamp) public {
        uint96 value = _backupStorage[user][timestamp];
        require(value != 0, "DSM: Record not in backup");
        
        bytes32 commitment;
        unchecked {
            commitment = keccak256(abi.encodePacked(user, timestamp, value, blockhash(block.number - 1)));
        }
        
        emit DataArchived(user, timestamp, commitment);
    }
    
    /**
     * @notice Purge backup storage after archival confirmation (Purge transition: S_Archived -> S_Purged)
     * @dev SSTORE with zero triggers gas refund (EIP-3529: ~4800 gas refund)
     * @param user The user address
     * @param timestamp The timestamp of the record to purge
     */
    function purgeArchivedData(address user, uint32 timestamp) public {
        require(_backupStorage[user][timestamp] != 0, "DSM: Not in backup");
        unchecked {
            delete _backupStorage[user][timestamp];
        }
        // SSTORE with zero triggers gas refund
        emit PurgeCompleted(user, timestamp);
    }
    
    /**
     * @notice Query recent data (within retention window)
     * @dev O(1) mapping lookup
     * @param user The user address
     * @param timestamp The timestamp to query
     */
    function getRecentData(address user, uint32 timestamp) public view returns (uint96) {
        return _activeStorage[user][timestamp];
    }
    
    /**
     * @notice Query historical data from backup
     * @dev O(1) mapping lookup
     * @param user The user address
     * @param timestamp The timestamp to query
     */
    function getHistoricalData(address user, uint32 timestamp) public view returns (uint96) {
        return _backupStorage[user][timestamp];
    }
    
    /**
     * @notice Get all timestamps for a user
     * @return Array of timestamps
     */
    function getUserTimestamps(address user) public view returns (uint32[] memory) {
        return _timestamps[user];
    }
    
    /**
     * @notice Get active storage count for a user
     */
    function getActiveCount(address user) public view returns (uint256) {
        return _timestamps[user].length;
    }
}