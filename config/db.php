<?php
class Database
{
    private $host;
    private $user;
    private $password;
    private $db;
    private $charset;

    public function connection()
    {
        // Load database credentials from .env file
        $env = parse_ini_file(__DIR__ . "/.env");

        $this->host     = $env["DB_HOST"];
        $this->user     = $env["DB_USER"];
        $this->password = $env["DB_PASS"];
        $this->db       = $env["DB_NAME"];
        $this->charset  = "utf8mb4";

        try {
            $dsn = "mysql:host=" . $this->host . ";dbname=" . $this->db . ";charset=" . $this->charset;
            $pdo = new PDO($dsn, $this->user, $this->password);
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            return $pdo;
        } catch (PDOException $e) {
            echo "Connection failed: " . $e->getMessage();
        }
    }
}
?>
