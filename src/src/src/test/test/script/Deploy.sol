// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "forge-std/Script.sol";
import "DSM.sol";
import "src/ArrayBaseline.sol";
import "src/src/MappingOnly.sol";

contract DeployScript is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        
        vm.startBroadcast(deployerPrivateKey);
        
        DSM dsm = new DSM();
        ArrayBaseline arrayBaseline = new ArrayBaseline();
        MappingOnly mappingOnly = new MappingOnly();
        
        vm.stopBroadcast();
        
        console.log("DSM deployed at:", address(dsm));
        console.log("ArrayBaseline deployed at:", address(arrayBaseline));
        console.log("MappingOnly deployed at:", address(mappingOnly));
    }
}
