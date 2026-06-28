CREATE TABLE users (
   userid INT AUTO_INCREMENT PRIMARY KEY,
   email VARCHAR(255) NOT NULL UNIQUE,
   password VARCHAR(255) NOT NULL,
   role VARCHAR(255) NOT NULL CHECK (role IN ('admin', 'user')),
   receive_emails TINYINT(1) DEFAULT 0
);

CREATE TABLE car (
    carid INT AUTO_INCREMENT PRIMARY KEY,
    make VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    trim VARCHAR(255) NOT NULL,
    year INT NOT NULL,
    miles INT NOT NULL,
    price FLOAT NOT NULL,
    vin VARCHAR(255) NOT NULL,
    color VARCHAR(255) NOT NULL,
    drivetype VARCHAR(10) NOT NULL,
    status VARCHAR(255) NOT NULL,
    description LONGTEXT NOT NULL
);

CREATE TABLE pictures (
    picid INT AUTO_INCREMENT PRIMARY KEY,
    carid INT NOT NULL,
    picNo INT NOT NULL,
    image_path VARCHAR(500) NOT NULL,
    is_main TINYINT(1) DEFAULT 0,
    focal_x FLOAT DEFAULT 50,
    focal_y FLOAT DEFAULT 50,
    FOREIGN KEY (carid) REFERENCES car(carid) ON DELETE CASCADE
);