# Dealership Backend API Documentation

## Base URL
```
http://localhost/dealership-project/backend/api/
```

---

## Authentication Endpoints

### Register
Creates a new user account.

**Endpoint:** `POST /register.php`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "receiveEmails": false
}
```

**Validation Rules:**
- `email`: Required, must be valid email format, must be unique
- `password`: Required, minimum 6 characters
- `receiveEmails`: Optional boolean, defaults to false

**Success Response (201):**
```json
{
  "status": "success",
  "message": "Registration successful"
}
```

**Error Responses:**
- `400`: Missing email/password
- `400`: Invalid email format
- `400`: Password less than 6 characters
- `409`: Email already registered
- `500`: Database error

---

### Login
Authenticates user and returns JWT token.

**Endpoint:** `POST /login.php`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Validation Rules:**
- `email`: Required, must be valid email format
- `password`: Required

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Login successful",
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Token Details:**
- Algorithm: HS256
- Payload: `{userid, iat (issued at), exp (expiration)}`
- Expiry: 1 hour from issue time

**Error Responses:**
- `400`: Missing email/password
- `400`: Invalid email format
- `401`: Invalid email or password
- `500`: Database error

---

## Car Endpoints

### Get All Cars
Retrieves all cars in inventory with main image.

**Endpoint:** `GET /get_cars.php`

**Query Parameters:** None

**Success Response (200):**
```json
{
  "status": "success",
  "data": [
    {
      "carid": 1,
      "make": "Toyota",
      "model": "Camry",
      "trim": "LE",
      "year": 2022,
      "miles": 45000,
      "price": 22999.99,
      "vin": "JTDKN3AU5J3072165",
      "status": "available",
      "description": "Well maintained sedan",
      "image_path": "http://localhost/dealership-project/backend/uploads/car_1_pic_1.jpg"
    }
  ]
}
```

**Response Details:**
- Returns cars ordered by `carid DESC` (newest first)
- `image_path`: URL of main image (`is_main=1`) or default placeholder
- Default image: `http://localhost/dealership-project/backend/uploads/default_car_image.jpg`

**Error Responses:**
- `500`: Connection failed

---

### Get Car by ID
Retrieves a single car by ID.

**Endpoint:** `GET /get_car_by_id.php`

**Query Parameters:**
```
id=1 (required, integer)
```

**Success Response (200):**
```json
{
  "status": "success",
  "data": {
    "carid": 1,
    "make": "Toyota",
    "model": "Camry",
    "trim": "LE",
    "year": 2022,
    "miles": 45000,
    "price": 22999.99,
    "vin": "JTDKN3AU5J3072165",
    "status": "available",
    "description": "Well maintained sedan"
  }
}
```

**Error Responses:**
- `400`: Missing or invalid id parameter
- `404`: Car not found
- `500`: Connection failed

---

### Add Car
Creates a new car listing.

**Endpoint:** `POST /add_car.php`

**Request Body (JSON or Form Data):**
```json
{
  "make": "Toyota",
  "model": "Camry",
  "trim": "LE",
  "year": 2022,
  "miles": 45000,
  "price": 22999.99,
  "vin": "JTDKN3AU5J3072165",
  "status": "available",
  "description": "Well maintained sedan"
}
```

**Validation Rules:**
- All fields required
- `make`, `model`, `trim`, `vin`, `status`, `description`: Text (XSS sanitized)
- `year`, `miles`: Integer
- `price`: Float

**Success Response (201):**
```json
{
  "status": "success",
  "message": "Car added successfully",
  "carid": 1
}
```

**Error Responses:**
- `400`: Missing required field
- `400`: Invalid number format
- `500`: Database error

---

### Update Car
Updates one or more fields of an existing car.

**Endpoint:** `POST /update_car.php`

**Request Body (JSON):**
```json
{
  "carid": 1,
  "make": "Toyota",
  "model": "Corolla",
  "price": 18999.99
}
```

**Validation Rules:**
- `carid`: Required, integer
- Only include fields to update
- Same validation as Add Car for field types
- `year`, `miles`, `price`: Integer fields (requires proper type conversion)

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Car updated successfully"
}
```

**Error Responses:**
- `400`: Missing carid
- `400`: Invalid carid format
- `400`: No valid fields to update
- `400`: Invalid number format
- `500`: Database error

---

### Delete Car
Deletes a car and all associated images (with file cleanup).

**Endpoint:** `POST /delete_car.php`

**Request Body (JSON):**
```json
{
  "carid": 1
}
```

**Validation Rules:**
- `carid`: Required, integer

**Deletion Process:**
1. Fetch all image paths from Pictures table
2. Delete from Car table (cascade deletes Pictures)
3. Delete physical files from `/uploads` directory

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Car deleted"
}
```

**Error Responses:**
- `400`: Missing carid
- `400`: Invalid carid format
- `404`: Car not found
- `500`: Database error

---

## Image Endpoints

### Get Car Images
Retrieves all images for a specific car.

**Endpoint:** `GET /get_car_images.php`

**Query Parameters:**
```
carid=1 (required, integer)
```

**Success Response (200):**
```json
{
  "status": "success",
  "data": [
    {
      "picid": 1,
      "image_path": "http://localhost/dealership-project/backend/uploads/car_1_pic_1.jpg",
      "is_main": 1,
      "picNo": 1
    },
    {
      "picid": 2,
      "image_path": "http://localhost/dealership-project/backend/uploads/car_1_pic_2.jpg",
      "is_main": 0,
      "picNo": 2
    }
  ]
}
```

**Response Details:**
- Ordered by `picNo` ascending
- `is_main`: 1 = main/cover image, 0 = regular image
- `image_path`: Full URL to uploaded image

**Error Responses:**
- `400`: Missing carid parameter
- `500`: Connection failed

---

### Upload Image
Uploads and stores a new car image.

**Endpoint:** `POST /add_single_image.php`

**Request (multipart/form-data):**
```
carid: 1 (integer, required)
image: <file> (required, image file)
```

**File Validation:**
- Maximum size: 10MB
- Allowed MIME types: `image/jpeg`, `image/png`, `image/gif`
- Checked via MIME type detection (not extension)

**Image Processing:**
- Filename: `car_{carid}_pic_{picNo}.{ext}`
- Example: `car_1_pic_3.jpg`
- `picNo` = auto-incremented per car
- First image (`picNo=1`) set as `is_main=1`

**Success Response (201):**
```json
{
  "status": "success",
  "data": {
    "picid": 1,
    "image_path": "http://localhost/dealership-project/backend/uploads/car_1_pic_1.jpg",
    "is_main": 1
  }
}
```

**Error Responses:**
- `400`: Missing carid or image
- `400`: Invalid carid format
- `400`: File too large (>10MB)
- `400`: Unsupported image type
- `500`: Database or file system error

---

### Delete Image
Deletes a single image and promotes next image as main if needed.

**Endpoint:** `POST /delete_image.php`

**Request Body (JSON):**
```json
{
  "picid": 1,
  "carid": 1
}
```

**Validation Rules:**
- `picid`: Required, integer
- `carid`: Required, integer

**Deletion Logic:**
1. Fetch image details and check if `is_main=1`
2. If main image: find next image and set it as main
3. Delete from Pictures table
4. Delete physical file from `/uploads`

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Image deleted"
}
```

**Error Responses:**
- `400`: Missing picid or carid
- `400`: Invalid picid or carid format
- `404`: Image not found
- `500`: Database or file system error

---

### Set Main Image
Sets a specific image as the main/cover image for a car.

**Endpoint:** `POST /set_is_main.php`

**Request Body (JSON):**
```json
{
  "picid": 2,
  "carid": 1
}
```

**Validation Rules:**
- `picid`: Required, integer
- `carid`: Required, integer

**Update Logic:**
1. Set all images for car to `is_main=0`
2. Set selected image to `is_main=1`

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Cover image updated"
}
```

**Error Responses:**
- `400`: Missing picid or carid
- `400`: Invalid picid or carid format
- `404`: Image not found
- `500`: Database error

---

## Response Format

### Success Response Structure
```json
{
  "status": "success",
  "message": "Optional message",
  "data": {},
  "carid": 123
}
```

### Error Response Structure
```json
{
  "status": "error",
  "message": "Error description"
}
```

### HTTP Status Codes
| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful GET, PUT, DELETE |
| 201 | Created | Successful POST creating resource |
| 400 | Bad Request | Invalid input, missing fields |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Email already registered |
| 500 | Server Error | Database or system error |

---

## CORS Headers
All responses include:
```
Access-Control-Allow-Origin: *
Content-Type: application/json; charset=UTF-8
Access-Control-Allow-Methods: GET, POST, OPTIONS, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With
```

Preflight OPTIONS requests return 200 OK.

---

## Database Schema Reference

### Users Table
```sql
CREATE TABLE Users (
  userid INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  receive_emails TINYINT(1) DEFAULT 0
);
```

### Car Table
```sql
CREATE TABLE Car (
  carid INT AUTO_INCREMENT PRIMARY KEY,
  make VARCHAR(255) NOT NULL,
  model VARCHAR(255) NOT NULL,
  trim VARCHAR(255) NOT NULL,
  year INT NOT NULL,
  miles INT NOT NULL,
  price FLOAT NOT NULL,
  vin VARCHAR(255) NOT NULL,
  status VARCHAR(255) NOT NULL,
  description LONGTEXT NOT NULL
);
```

### Pictures Table
```sql
CREATE TABLE Pictures (
  picid INT AUTO_INCREMENT PRIMARY KEY,
  carid INT NOT NULL,
  picNo INT NOT NULL,
  image_path VARCHAR(500) NOT NULL,
  is_main TINYINT(1) DEFAULT 0,
  FOREIGN KEY (carid) REFERENCES Car(carid) ON DELETE CASCADE
);
```

---

## Common Error Scenarios

### Invalid Email
```json
{
  "status": "error",
  "message": "Invalid email format"
}
```

### Password Too Short
```json
{
  "status": "error",
  "message": "Password must be at least 6 characters"
}
```

### Email Already Exists
```json
{
  "status": "error",
  "message": "Email already registered"
}
```

### File Too Large
```json
{
  "status": "error",
  "message": "File too large"
}
```

### Car Not Found
```json
{
  "status": "error",
  "message": "Car not found"
}
```

---

## Implementation Notes

- All string inputs are sanitized to prevent XSS (strip_tags, trim)
- Database transactions used for multi-step operations
- Foreign key cascade delete removes Pictures when Car deleted
- Image files stored in `/uploads` directory with server path
- API returns full URLs for images so React can display them
- No authentication required for read operations (GET)
- File upload max size: 10MB (configurable)
