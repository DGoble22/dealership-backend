<?php
    require_once "../config/db.php";
    require_once "../api_header.php";

    try {
        //Database connection
        $db = new Database();
        $conn = $db->connection();

        //Input Validation
        if(!isset($_GET["id"])){
            http_response_code(400);
            echo json_encode([
                "status" => "error",
                "message" => "Missing id parameter"]);
            exit();
        }
        $id = filter_var($_GET["id"], FILTER_VALIDATE_INT);
        if($id === false){
            http_response_code(400);
            echo json_encode(["status" => "error", "message" => "Invalid id"]);
            exit;
        }

        //SQL
        $sql = "SELECT * FROM Car WHERE carid = :id";
        $stmt = $conn->prepare($sql);
        $stmt->execute(['id' => $id]);
        $result = $stmt->fetch(PDO::FETCH_ASSOC);

        //Checks to see if car exists
        if($result){
            echo json_encode(["status" => "success", "data" => $result]);
        } else {
            http_response_code(404); // ID valid but car not found
            echo json_encode(["status" => "error", "message" => "Car not found"]);
        }

    } catch (PDOException $e) {
        http_response_code(500);
        echo json_encode(["status" => "error",
            "message" => "connection failed: " . $e->getMessage()]);
    }
?>
