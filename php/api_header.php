<?php
    //Common headers for ALL API responses
    header("Access-Control-Allow-Origin: *"); //Allows React
    header("Content-Type: application/json; charset=UTF-8"); //Output encoding
    header("Access-Control-Allow-Methods: GET, POST, OPTIONS, DELETE");
    header("Access-Control-Allow-Headers: Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With");

    //Preflight request exit early
    if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
        http_response_code(200);
        exit;
    }
?>