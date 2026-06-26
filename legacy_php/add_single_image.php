<?php
    require_once "../config/db.php";
    require_once "../api_header.php";

    // Imput validation
    $carid = filter_var($_POST["carid"], FILTER_VALIDATE_INT);
    if (!$carid || !isset($_FILES['image'])) {
        http_response_code(400);
        echo json_encode(["status" => "error", "message" => "Missing car ID or image"]);
        exit;
    }

    // File checks
    $file = $_FILES['image'];
    $maxBytes = 10 * 1024 * 1024; // 10MB
    if ($file['error'] !== UPLOAD_ERR_OK) {
        http_response_code(400);
        echo json_encode(["status" => "error", "message" => "File upload error"]);
        exit;
    }
    if ($file['size'] > $maxBytes) {
        http_response_code(400);
        echo json_encode(["status" => "error", "message" => "File too large"]);
        exit;
    }

    // Validate MIME type
    $finfo = new finfo(FILEINFO_MIME_TYPE);
    $mime = $finfo->file($file['tmp_name']);
    $allowed = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/gif' => 'gif'];
    if (!isset($allowed[$mime])) {
        http_response_code(400);
        echo json_encode(["status" => "error", "message" => "Unsupported image type"]);
        exit;
    }

    $conn = null;
    try {
        $db = new Database();
        $conn = $db->connection();
        $conn->beginTransaction();

        // Get the next Picture Number (picNo)
        $stmt = $conn->prepare("SELECT MAX(picNo) as maxNo FROM Pictures WHERE carid = ?");
        $stmt->execute([$carid]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        $picNo = (isset($row['maxNo']) ? $row['maxNo'] : 0) + 1;

        // file path setup
        $uploadDir = __DIR__ . "/../uploads/";
        $file = $_FILES['image'];
        $ext = pathinfo($file['name'], PATHINFO_EXTENSION);

        // Create a clean filename eg: car_105_pic_1.jpg
        $filename = "car_{$carid}_pic_{$picNo}." . $ext;
        $targetPath = $uploadDir . $filename;

        if (move_uploaded_file($file['tmp_name'], $targetPath)) {
            // Save to Database save the full URL so React can display it easily
            $dbPath = "http://localhost/dealership-project/backend/uploads/" . $filename;

            // If this is the first image, make it the main one
            $isMain = ($picNo === 1) ? 1 : 0;

            $sql = "INSERT INTO Pictures (carid, picNo, image_path, is_main) VALUES (?, ?, ?, ?)";
            $stmt = $conn->prepare($sql);
            $stmt->execute([$carid, $picNo, $dbPath, $isMain]);

            $newPicId = $conn->lastInsertId();

            $conn->commit();
            http_response_code(201);
            echo json_encode([
                "status" => "success",
                "data" => [
                    "picid" => $newPicId,
                    "image_path" => $dbPath,
                    "is_main" => $isMain
                ]
            ]);
        } else {
            $absPath = realpath($uploadDir);
            $sysError = error_get_last();
            throw new Exception("Failed to move file. Trying to save to: '" . $targetPath . "' (Resolved: " . $absPath . "). System Error: " . $sysError['message']);
        }

    } catch (Exception $e) {
        if($conn && $conn->inTransaction()){$conn->rollBack();}
        http_response_code(500);
        echo json_encode(["status" => "error", "message" => $e->getMessage()]);
    }
?>