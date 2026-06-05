// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

/**
 * @title Array Baseline Contract
 * @notice Traditional array-based storage with shift deletion (O(n²) complexity)
 * @dev Used as baseline for comparison in the paper
 */
contract ArrayBaseline {
    
    struct DataRecord {
        uint256 timestamp;
        uint256 value;
    }
    
    /// @dev Main storage array - shifting required for deletion
    mapping(address => DataRecord[]) public records;
    
    /// @dev Historical data after migration
    mapping(address => DataRecord[]) public historicalData;
    
    event DataStored(address indexed user, uint256 timestamp, uint256 value);
    event DataMigrated(address indexed user, uint256 count);
    
    /**
     * @notice Store a data record
     * @dev O(1) push, but deletion will be O(n)
     */
    function storeData(uint256 value) public {
        uint256 timestamp = block.timestamp;
        records[msg.sender].push(DataRecord(timestamp, value));
        emit DataStored(msg.sender, timestamp, value);
    }
    
    /**
     * @notice Batch store multiple records
     */
    function batchStoreData(uint256[] calldata values) public {
        for (uint256 i = 0; i < values.length; i++) {
            uint256 offset = (values.length - i) * 1 seconds;
            uint256 timestamp = block.timestamp >= offset ? block.timestamp - offset : 0;
            records[msg.sender].push(DataRecord(timestamp, values[i]));
            emit DataStored(msg.sender, timestamp, values[i]);
        }
    }
    
    /**
     * @notice Migrate stale data - O(n²) due to shifting on each deletion
     * @dev This is the key inefficiency: each _removeElement call triggers O(n) shift
     * @param user The user address
     * @param before Timestamp cutoff (migrate records older than this)
     */
    function migrateData(address user, uint256 before) public {
        DataRecord[] storage userRecords = records[user];
        uint256 migratedCount = 0;
        
        for (uint256 i = 0; i < userRecords.length; i++) {
            if (userRecords[i].timestamp < before) {
                historicalData[user].push(userRecords[i]);
                _removeElement(userRecords, i);
                if (i > 0) i--; // Adjust index after removal (only if not at start)
                migratedCount++;
            }
        }
        
        emit DataMigrated(user, migratedCount);
    }
    
    /**
     * @dev Internal function that causes O(n) shift on EVERY deletion
     * @param arr The storage array
     * @param idx The index to remove
     */
    function _removeElement(DataRecord[] storage arr, uint256 idx) internal {
        for (uint256 i = idx; i + 1 < arr.length; i++) {
            arr[i] = arr[i + 1];
        }
        arr.pop();
    }
    
    /**
     * @notice Query a record by index (inefficient for large datasets)
     */
    function getRecord(address user, uint256 index) public view returns (uint256 timestamp, uint256 value) {
        DataRecord memory record = records[user][index];
        return (record.timestamp, record.value);
    }
    
    /**
     * @notice Get total record count
     */
    function getRecordCount(address user) public view returns (uint256) {
        return records[user].length;
    }
}