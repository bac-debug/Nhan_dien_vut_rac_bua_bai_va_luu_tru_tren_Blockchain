// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ViolationRegistry
 * @notice Lưu trữ mã băm SHA-256 của hình ảnh vi phạm vứt rác lên Ethereum Sepolia Testnet
 * @dev Deploy trên Remix IDE với Injected Provider (MetaMask)
 *
 * === HƯỚNG DẪN DEPLOY ===
 * 1. Vào https://remix.ethereum.org
 * 2. Tạo file mới: contracts/ViolationRegistry.sol
 * 3. Paste toàn bộ nội dung file này vào
 * 4. Tab "Solidity compiler" → chọn version 0.8.20 → "Compile"
 * 5. Tab "Deploy & run" → Environment: "Injected Provider - MetaMask"
 *    (MetaMask phải đang ở mạng Sepolia Testnet)
 * 6. Click "Deploy" → MetaMask popup → Confirm
 * 7. Sau khi deploy xong, copy "Deployed contract address" (0x...)
 * 8. Paste địa chỉ đó vào index.html tại dòng: const CONTRACT_ADDRESS = "..."
 */
contract ViolationRegistry {

    // ── Cấu trúc lưu trữ mỗi vi phạm ──
    struct ViolationRecord {
        uint256 violationId;     // ID vi phạm từ hệ thống Python
        string  imageHash;       // SHA-256 hex string của ảnh bằng chứng
        uint256 blockTimestamp;  // Unix timestamp lúc ghi lên chain
        address reporter;        // Địa chỉ ví MetaMask ghi vi phạm
    }

    // ── Lưu trữ ──
    ViolationRecord[] public records;

    // Mapping: violationId → index trong records[] để tra nhanh
    mapping(uint256 => uint256) private idToIndex;
    mapping(uint256 => bool)    private idExists;

    // ── Events ──
    event ViolationLogged(
        uint256 indexed violationId,
        string  imageHash,
        address indexed reporter,
        uint256 timestamp
    );

    // ── Functions ──

    /**
     * @notice Ghi vi phạm mới lên blockchain
     * @param violationId  ID vi phạm từ hệ thống Python (database SQLite)
     * @param imageHash    SHA-256 hash của ảnh bằng chứng (hex string, không có 0x prefix)
     */
    function logViolation(uint256 violationId, string calldata imageHash) external {
        require(bytes(imageHash).length == 64, "Hash phai la 64 ky tu hex (SHA-256)");
        require(!idExists[violationId], "Vi pham nay da duoc ghi truoc do");

        idToIndex[violationId] = records.length;
        idExists[violationId]  = true;

        records.push(ViolationRecord({
            violationId:    violationId,
            imageHash:      imageHash,
            blockTimestamp: block.timestamp,
            reporter:       msg.sender
        }));

        emit ViolationLogged(violationId, imageHash, msg.sender, block.timestamp);
    }

    /**
     * @notice Kiểm tra một hash có khớp với vi phạm đã ghi không
     * @param violationId  ID vi phạm cần xác minh
     * @param imageHash    Hash cần kiểm tra
     * @return bool        true nếu hash khớp
     */
    function verifyViolation(uint256 violationId, string calldata imageHash) external view returns (bool) {
        if (!idExists[violationId]) return false;
        uint256 idx = idToIndex[violationId];
        return keccak256(bytes(records[idx].imageHash)) == keccak256(bytes(imageHash));
    }

    /**
     * @notice Lấy thông tin vi phạm theo violationId từ hệ thống Python
     */
    function getByViolationId(uint256 violationId) external view
        returns (string memory imageHash, uint256 timestamp, address reporter)
    {
        require(idExists[violationId], "Vi pham chua duoc ghi len blockchain");
        uint256 idx = idToIndex[violationId];
        ViolationRecord memory r = records[idx];
        return (r.imageHash, r.blockTimestamp, r.reporter);
    }

    /**
     * @notice Lấy thông tin vi phạm theo index trong mảng records
     */
    function getRecord(uint256 index) external view
        returns (uint256 violationId, string memory imageHash, uint256 timestamp, address reporter)
    {
        require(index < records.length, "Index out of bounds");
        ViolationRecord memory r = records[index];
        return (r.violationId, r.imageHash, r.blockTimestamp, r.reporter);
    }

    /**
     * @notice Tổng số vi phạm đã ghi lên blockchain
     */
    function totalRecords() external view returns (uint256) {
        return records.length;
    }

    /**
     * @notice Kiểm tra vi phạm có tồn tại trên chain không
     */
    function exists(uint256 violationId) external view returns (bool) {
        return idExists[violationId];
    }
}
