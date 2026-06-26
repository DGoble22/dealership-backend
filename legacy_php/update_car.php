<?php
    require_once "../config/db.php";
    require_once "../api_header.php";

    //Get raw data from stream need to read JSON sent from React
    $raw_data = file_get_contents("php://input");
    $data = json_decode($raw_data, True);
    $fields = [];
    $values = [];

    // Validate carid was provided
    if(!isset($data['carid'])|| $data['carid'] === ""){
        echo json_encode(["status" => "error", "message" => "Car id is required"]);
        exit();
    }

    // Sets carid variable and removes from associative array
    $carid = filter_var($data["carid"], FILTER_VALIDATE_INT);
    if($carid === false){echo json_encode(["status" => "error", "message" => "Car id integer expected"]); exit(); }
    unset($data['carid']);

    $conn = null;
    try{
        //Database connection
        $db = new Database();
        $conn = $db->connection();
        $conn->beginTransaction();

        //Dynamic loop with validation and sanitization
        $intColumns = ['year', 'price', 'miles'];
        $stringColumns = ['make', 'model', 'trim', 'vin', 'status', 'description'];
        foreach ($data as $column => $value) {
            if(in_array($column, array_merge($stringColumns, $intColumns))) {
                if(in_array($column, $intColumns)) {
                    //Integer sanitization
                    $clean_int = filter_var($value, FILTER_SANITIZE_NUMBER_INT);
                    if ($clean_int === false) {
                        echo json_encode(["status" => "error", "message" => "Invalid number for: $column"]);
                        exit();
                    }
                    $final_value = (int)$clean_int;
                }
                //String sanitization
                else{
                    $final_value = trim(strip_tags($value));
                }
                $fields[] = "$column = ?";
                $values[] = $final_value;
            }
        }

        if(empty($fields)){
            echo json_encode(["status" => "error", "message" => "No valid fields to update"]);
            exit();
        }


        $values[] = $carid; // Add id at the end for the where clause
        $sql = "UPDATE Car SET ".implode(", ", $fields)." WHERE carid = ?";
        $stmt = $conn->prepare($sql);
        $stmt->execute($values);

        if($stmt->rowCount() > 0){
            echo json_encode(["status" => "success", "message" => "Car updated successfully"]);
        } else {
            echo json_encode(["status" => "error", "message" => "No Changes Made"]);
        }
        http_response_code(200);
        $conn->commit();
    } catch (PDOException $e) {
        if($conn && $conn->inTransaction()){$conn->rollBack();}
        http_response_code(500);
        echo json_encode(array("status" => "error", "message" => "Database Error: " . $e->getMessage()));
    }
?>