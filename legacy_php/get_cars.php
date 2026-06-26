<?php
    require_once "../config/db.php";
    require_once "../api_header.php";

    try{
        //Database connection
        $db = new Database();
        $conn = $db->connection();

        //SQL
        $sql = "SELECT c.*, p.image_path 
                FROM Car c
                LEFT JOIN Pictures p ON c.carid = p.carid AND p.is_main = 1
                ORDER BY c.carid DESC";
        $stmt = $conn->prepare($sql);
        $stmt->execute();
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

        //output to JSON
        http_response_code(200);
        echo json_encode(["status" => "success", "data" => $result]);

    } catch (PDOException $e) {
        http_response_code(500);
        echo json_encode([
            "status" => "error",
            "message" => "connection failed: " . $e->getMessage()]);
    }
?>