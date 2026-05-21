<?php
    require_once "../config/db.php";
    require_once "../api_header.php";

    //Get raw data from stream need to read JSON sent from React
    $data = $_POST;

    // Validate required fields
    $required = ["make", "model", "trim", "year", "miles", "price", "vin", "status", "description"];
    foreach ($required as $field) {
        if(!isset($data[$field]) || $data[$field] === ""){
            http_response_code(400);
            echo json_encode(["status" => "error", "message" => "Missing required field: ". $field]);
            exit;
        }
    }

    //Sanitize Strings to prevent XSS
    $make = trim(strip_tags($data["make"]));
    $model = trim(strip_tags($data["model"]));
    $trim = trim(strip_tags($data["trim"]));
    $vin = trim(strip_tags($data["vin"]));
    $status = trim(strip_tags($data["status"]));
    $description = strip_tags($data["description"]);

    //Number validation
    $year = filter_var($data["year"], FILTER_VALIDATE_INT);
    $miles = filter_var($data["miles"], FILTER_VALIDATE_INT);
    $price = filter_var($data["price"], FILTER_VALIDATE_FLOAT);
    if($year === false || $miles === false || $price === false){
        http_response_code(400);
        echo json_encode(["status" => "error", "message" => "Invalid number"]);
        exit;
    }

    $conn = null;
    try{
        $db = new Database();
        $conn = $db->connection();
        $conn->beginTransaction();

        // SQL for data upload
        $sql = "INSERT INTO Car (make, model, trim, year, miles, price, vin, status, description) 
                VALUES (:make, :model, :trim, :year, :miles, :price, :vin, :status, :description)";
        $stmt = $conn->prepare($sql);
        $stmt->execute([
            "make" => $make,
            "model" => $model,
            "trim" => $trim,
            "year" => $year,
            "miles" => $miles,
            "price" => $price,
            "vin" => $vin,
            "status" => $status,
            "description" => $description
        ]);

        $newCarId = $conn->lastInsertId();

        //Success Response
        $conn->commit();
        http_response_code(201); // 201 = Created
        echo json_encode(["status" => "success", "message" => "Car added successfully", "carid" => $newCarId]);

    } catch(PDOException $e) {
        if($conn && $conn->inTransaction()){$conn->rollBack();}
        http_response_code(500);
        echo json_encode(array("status" => "error", "message" => "Database Error: " . $e->getMessage()));
    }
?>