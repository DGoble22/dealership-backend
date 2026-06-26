<?php
    require_once "../config/db.php";
    require_once "../api_header.php";

    // Get raw JSON data from request
    $input = file_get_contents("php://input");
    $data = json_decode($input, true);

    // Validate required fields
    if (!isset($data["email"]) || !isset($data["password"])) {
        http_response_code(400);
        echo json_encode(["status" => "error", "message" => "Email and password are required"]);
        exit;
    }

    // Sanitize email
    $email = filter_var(trim($data["email"]), FILTER_SANITIZE_EMAIL);

    // Validate email format
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        http_response_code(400);
        echo json_encode(["status" => "error", "message" => "Invalid email format"]);
        exit;
    }

    // Validate password length
    if (strlen($data["password"]) < 6) {
        http_response_code(400);
        echo json_encode(["status" => "error", "message" => "Password must be at least 6 characters"]);
        exit;
    }

    // Get receive emails preference (default to false)
    $receiveEmails = isset($data["receiveEmails"]) ? (bool)$data["receiveEmails"] : false;

    $conn = null;
    try {
        $db = new Database();
        $conn = $db->connection();
        $conn->beginTransaction();

        // Check if email already exists
        $sql = "SELECT userid FROM Users WHERE email = :email";
        $stmt = $conn->prepare($sql);
        $stmt->execute(["email" => $email]);

        if ($stmt->fetch()) {
            http_response_code(409);
            echo json_encode(["status" => "error", "message" => "Email already registered"]);
            exit;
        }

        // Hash password
        $hashedPassword = password_hash($data["password"], PASSWORD_DEFAULT);

        // Insert new user
        $sql= " INSERT INTO Users (email, password, receive_emails)
                VALUES (:email, :password, :receive_emails)";
        $stmt = $conn->prepare($sql);
        $stmt->execute([
            "email" => $email,
            "password" => $hashedPassword,
            "receive_emails" => $receiveEmails ? 1 : 0
        ]);

        $conn->commit();
        http_response_code(201);
        echo json_encode([
            "status" => "success",
            "message" => "Registration successful",
        ]);

    } catch (PDOException $e) {
        if($conn && $conn->inTransaction()){$conn->rollBack();}
        http_response_code(500);
        echo json_encode(["status" => "error", "message" => "Database error: " . $e->getMessage()]);
    }
?>

