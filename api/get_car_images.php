<?php
    require_once "../config/db.php";
    require_once "../api_header.php";

    try{
        //Database connection
        $db = new Database();
        $conn = $db->connection();

        $carid = isset($_GET["carid"]) ? filter_var($_GET["carid"], FILTER_VALIDATE_INT) : null;
        if($carid === null){
            http_response_code(400);
            echo json_encode(["status" => "error", "message" => "Missing carid parameter"]);
            exit;
        }

        //SQL
        $sql = "SELECT picid, image_path, is_main, picNo FROM Pictures WHERE carid = ? ORDER BY picNo";
        $stmt = $conn->prepare($sql);
        $stmt->execute([$carid]);
        $result = $stmt->fetchAll(PDO::FETCH_ASSOC);

        // image logic (& allows for modification of $result array)
        foreach($result as &$car){
            if($car["image_path"]){
                $car["image_path"] = "http://localhost/dealership-project/backend/uploads/" . basename($car["image_path"]);
            } else {
                //Fallback image
                $car["image_path"] = "http://localhost/dealership-project/backend/uploads/default_car_image.jpg";
            }
        }

        //Output to JSON
        http_response_code(200);
        echo json_encode(["status" => "success", "data" => $result]);

    } catch (PDOException $e) {
        http_response_code(500);
        echo json_encode([
            "status" => "error",
            "message" => "connection failed: " . $e->getMessage()]);
    }
?>
