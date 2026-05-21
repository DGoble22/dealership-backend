<?php
    require_once "../config/db.php";
    require_once "../api_header.php";

    //Get raw data from stream need to read JSON sent from React
    $data = json_decode(file_get_contents("php://input"), true);
    $picid = $data["picid"];
    $carid = $data["carid"];

    if(!isset($data["picid"]) || (!isset($data["carid"]))){
        http_response_code(400);
        echo json_encode(["status" => "error", "message" => "Missing required fields"]);
        exit;
    }

    // Validate integers
    $carid = filter_var($data["carid"], FILTER_VALIDATE_INT);
    $picid = filter_var($data["picid"], FILTER_VALIDATE_INT);
    if($carid === false){echo json_encode(["status" => "error", "message" => "Car id integer expected"]); exit(); }
    if($picid === false){echo json_encode(["status" => "error", "message" => "Picture id integer expected"]); exit(); }
    unset($data['carid']);
    unset($data['picid']);

    $conn = null;
    try {
        $db = new Database();
        $conn = $db->connection();
        $conn->beginTransaction();

        // set all images to not main for the car
        $stmt = $conn->prepare("UPDATE Pictures SET is_main = 0 WHERE carid = ?");
        $stmt->execute([$carid]);

        // set selected image to main
        $stmt = $conn->prepare("UPDATE Pictures SET is_main = 1 WHERE picid = ?");
        $stmt->execute([$picid]);

        $conn->commit();
        http_response_code(200);
        echo json_encode(["status" => "success", "message" => "Cover image updated"]);

    } catch (Exception $e) {
        if($conn && $conn->inTransaction()){$conn->rollBack();}
        http_response_code(500);
        echo json_encode(["status" => "error", "message" => $e->getMessage()]);
}
?>