# Smart Contract for AgroPulse Permits
# SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title AgroPulsePermit
 * @dev NFT-based permit system for pay-per-service AI diagnoses
 * Each permit represents a single-use authorization to access the AI diagnosis service
 */
contract AgroPulsePermit is ERC721, Ownable {
    using Counters for Counters.Counter;
    Counters.Counter private _tokenIds;

    // Permit metadata
    struct Permit {
        string permitType;      // "diagnosis", "premium", etc.
        bool isUsed;            // Has this permit been consumed?
        uint256 issuedAt;       // Timestamp of issuance
        uint256 usedAt;         // Timestamp of use (0 if not used)
        address farmer;         // Farmer who owns the permit
    }

    // Mapping from token ID to permit details
    mapping(uint256 => Permit) public permits;

    // Events
    event PermitMinted(uint256 indexed tokenId, address indexed farmer, string permitType);
    event PermitUsed(uint256 indexed tokenId, address indexed farmer, uint256 usedAt);

    constructor() ERC721("AgroPulse Permit", "AGRO") {}

    /**
     * @dev Mint a new permit NFT
     * @param to Address of the farmer receiving the permit
     * @param permitType Type of service permit (diagnosis, premium, etc.)
     * @return tokenId The ID of the newly minted permit
     */
    function mintPermit(address to, string memory permitType) 
        public 
        onlyOwner 
        returns (uint256) 
    {
        _tokenIds.increment();
        uint256 newTokenId = _tokenIds.current();

        _mint(to, newTokenId);

        permits[newTokenId] = Permit({
            permitType: permitType,
            isUsed: false,
            issuedAt: block.timestamp,
            usedAt: 0,
            farmer: to
        });

        emit PermitMinted(newTokenId, to, permitType);

        return newTokenId;
    }

    /**
     * @dev Mark a permit as used (consumed)
     * @param tokenId The permit token ID to mark as used
     * @return success Whether the operation was successful
     */
    function usePermit(uint256 tokenId) 
        public 
        onlyOwner 
        returns (bool) 
    {
        require(_exists(tokenId), "Permit does not exist");
        require(!permits[tokenId].isUsed, "Permit already used");

        permits[tokenId].isUsed = true;
        permits[tokenId].usedAt = block.timestamp;

        emit PermitUsed(tokenId, permits[tokenId].farmer, block.timestamp);

        return true;
    }

    /**
     * @dev Check if a permit is valid (exists and not used)
     * @param tokenId The permit token ID to check
     * @return valid Whether the permit is valid
     */
    function isPermitValid(uint256 tokenId) 
        public 
        view 
        returns (bool) 
    {
        return _exists(tokenId) && !permits[tokenId].isUsed;
    }

    /**
     * @dev Get permit details
     * @param tokenId The permit token ID
     * @return Permit struct with all details
     */
    function getPermit(uint256 tokenId) 
        public 
        view 
        returns (Permit memory) 
    {
        require(_exists(tokenId), "Permit does not exist");
        return permits[tokenId];
    }

    /**
     * @dev Get all permits owned by an address
     * @param farmer The farmer's address
     * @return Array of token IDs owned by the farmer
     */
    function getPermitsByFarmer(address farmer) 
        public 
        view 
        returns (uint256[] memory) 
    {
        uint256 balance = balanceOf(farmer);
        uint256[] memory result = new uint256[](balance);
        uint256 counter = 0;

        for (uint256 i = 1; i <= _tokenIds.current(); i++) {
            if (_exists(i) && ownerOf(i) == farmer) {
                result[counter] = i;
                counter++;
            }
        }

        return result;
    }

    /**
     * @dev Override transfer to prevent permit trading
     * Permits are non-transferable once minted
     */
    function _transfer(
        address from,
        address to,
        uint256 tokenId
    ) internal virtual override {
        require(false, "Permits are non-transferable");
    }
}
