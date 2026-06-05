// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

/**
 * @title Mapping-Only Baseline Contract
 * @notice Represents prior art: timestamp-keyed mapping without copy-based migration
 * @dev Used as baseline (mapping-only prior approach) in the paper
 */
contract MappingOnly {
    
    /// @dev Active storage using mappings (O(1) access)
    mapping(address => mapping(uint256 => uint256)) public storageData;
    
    /// @dev Timestamp index for iteration
    mapping(address => uint256[]) public timestamps;
    
    /// @dev Flag for stale data (not actually deleted - remains on-chain)
    mapping(address => mapping(uint256 => bool)) public isStale;
    
    event DataStored(address indexed user, uint256 timestamp, uint256 value);
    event DataMarkedStale(address indexed user, uint256 timestamp);
    
    /**
     * @notice Store a data record
     * @dev O(1) write - efficient
     */
    function storeData(uint256 value) public {
        uint256 timestamp = block.timestamp;
        storageData[msg.sender][timestamp] = value;
        timestamps[msg.sender].push(timestamp);
        emit DataStored(msg.sender, timestamp, value);
    }
    
    /**
     * @notice Batch store multiple records
     */
    function batchStoreData(uint256[] calldata values) public {
        for (uint256 i = 0; i < values.length; i++) {
            uint256 offset = (values.length - i) * 1 seconds;
            uint256 timestamp = block.timestamp >= offset ? block.timestamp - offset : 0;
            storageData[msg.sender][timestamp] = values[i];
            timestamps[msg.sender].push(timestamp);
            emit DataStored(msg.sender, timestamp, values[i]);
        }
    }
    
    /**
     * @notice Mark stale data (but NOT delete - data remains on-chain)
     * @dev This is the inefficiency of mapping-only: stale data never removed
     * @param user The user address
     * @param timestamp The timestamp to mark stale
     */
    function markStale(address user, uint256 timestamp) public {
        require(storageData[user][timestamp] != 0, "MappingOnly: Record not found");
        isStale[user][timestamp] = true;
        emit DataMarkedStale(user, timestamp);
    }

    /**
     * @notice Migrate stale data - per-record deletion (O(n) total, but less efficient than batch copy)
     * @dev This represents prior art: each stale record requires explicit deletion
     * @param user The user address
     * @param before Timestamp cutoff (migrate records older than this)
     */
    function migrateData(address user, uint256 before) public {
        uint256[] storage userTimestamps = timestamps[user];
        uint256 migratedCount = 0;

        for (uint256 i = 0; i < userTimestamps.length; i++) {
            uint256 ts = userTimestamps[i];
            if (ts < before && storageData[user][ts] != 0) {
                // Per-record delete (less efficient than DSM's batch copy)
                delete storageData[user][ts];
                isStale[user][ts] = true;
                migratedCount++;
            }
        }

        emit DataMarkedStale(user, migratedCount);
    }
    
    /**
     * @notice Get active records (excluding stale)
     * @dev Requires iterating all timestamps - O(n) per query
     * @param user The user address
     */
    function getActiveRecords(address user) public view returns (uint256[] memory timestamps_, uint256[] memory values_) {
        uint256[] storage userTimestamps = timestamps[user];
        uint256 activeCount = 0;
        
        // First pass: count active records
        for (uint256 i = 0; i < userTimestamps.length; i++) {
            if (!isStale[user][userTimestamps[i]]) {
                activeCount++;
            }
        }
        
        // Second pass: collect active records
        timestamps_ = new uint256[](activeCount);
        values_ = new uint256[](activeCount);
        uint256 idx = 0;
        for (uint256 i = 0; i < userTimestamps.length; i++) {
            uint256 ts = userTimestamps[i];
            if (!isStale[user][ts]) {
                timestamps_[idx] = ts;
                values_[idx] = storageData[user][ts];
                idx++;
            }
        }
    }
    
    /**
     * @notice Query any record by timestamp
     */
    function getRecord(address user, uint256 timestamp) public view returns (uint256) {
        return storageData[user][timestamp];
    }
}