<?php
    // Include Database class
    require_once './config/db.php';

    // Set the header to JSON
    header('Content-type: application/json');

    try{
        // Instantiate the class and get the connection
        $db = new Database();
        $conn = $db->connection();

        // Try to insert a test car
        $sql = "INSERT INTO Car (make, model, trim, year, miles, price, vin, status, description)
            VALUES (:make, :model, :trim, :year, :miles, :price, :vin, :status, :description)";

        $stmt = $conn->prepare($sql);
        $stmt->execute([
            'make' => 'Chevrolet',
            'model' => 'Tahoe',
            'trim' => 'PPV',
            'year' => 2018,
            'miles' => 206000,
            'price' => 15000,
            'vin' => 'xxxxxxxxxxxxxxxxx',
            'status' => 'available',
            'description' => 'personal vehicle'
        ]);

        echo json_encode([
            "status" => "success",
            "message" => "Car created!",
            "car_id" => $conn->lastInsertId()
        ]);

    } catch (PDOException $e) {
        http_response_code(500);
        echo json_encode([
            "status" => "error",
            "message" => "connection failed: " . $e->getMessage()
        ]);
    }
?>