# API Quick Reference & Examples

## cURL Examples

### Register
```bash
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "receiveEmails": false
  }'
```

### Login
```bash
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### Get All Cars
```bash
curl http://localhost:5000/cars
```

### Get Single Car
```bash
curl http://localhost:5000/cars/1
```

### Add Car
```bash
curl -X POST http://localhost:5000/cars \
  -H "Content-Type: application/json" \
  -d '{
    "make": "Toyota",
    "model": "Camry",
    "trim": "LE",
    "year": 2022,
    "miles": 45000,
    "price": 22999.99,
    "vin": "JTDKN3AU5J3072165",
    "status": "available",
    "description": "Well maintained"
  }'
```

### Update Car
```bash
curl -X PUT http://localhost:5000/cars/1 \
  -H "Content-Type: application/json" \
  -d '{
    "price": 21999.99,
    "miles": 50000
  }'
```

### Delete Car
```bash
curl -X DELETE http://localhost:5000/cars/1
```

### Get Car Images
```bash
curl http://localhost:5000/cars/1/images
```

### Upload Image
```bash
curl -X POST http://localhost:5000/cars/1/images \
  -F "image=@/path/to/image.jpg"
```

### Delete Image
```bash
curl -X DELETE http://localhost:5000/cars/1/images/5
```

### Set Main Image
```bash
curl -X PUT http://localhost:5000/cars/1/images/5/main
```

---

## JavaScript/Fetch Examples

### Register
```javascript
const register = async (email, password, receiveEmails = false) => {
  const response = await fetch('http://localhost:5000/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, receiveEmails })
  });
  return response.json();
};

const result = await register('user@example.com', 'password123', true);
if (result.status === 'success') {
  console.log('Registration successful');
}
```

### Login & Store Token
```javascript
const login = async (email, password) => {
  const response = await fetch('http://localhost:5000/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  const result = await response.json();
  if (result.status === 'success') {
    localStorage.setItem('authToken', result.token);
  }
  return result;
};
```

### Get Cars
```javascript
const getCars = async () => {
  const response = await fetch('http://localhost:5000/cars');
  const result = await response.json();
  if (result.status === 'success') {
    return result.data;
  }
  return [];
};

const cars = await getCars();
console.log(cars);
```

### Add Car
```javascript
const addCar = async (carData) => {
  const response = await fetch('http://localhost:5000/cars', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(carData)
  });
  return response.json();
};

const result = await addCar({
  make: 'Toyota',
  model: 'Camry',
  trim: 'LE',
  year: 2022,
  miles: 45000,
  price: 22999.99,
  vin: 'JTDKN3AU5J3072165',
  status: 'available',
  description: 'Well maintained'
});

if (result.status === 'success') {
  console.log('Car added with ID:', result.carid);
}
```

### Update Car
```javascript
const updateCar = async (carId, updates) => {
  const response = await fetch(`http://localhost:5000/cars/${carId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates)
  });
  return response.json();
};

const result = await updateCar(1, { price: 21999.99, miles: 50000 });
```

### Delete Car
```javascript
const deleteCar = async (carId) => {
  const response = await fetch(`http://localhost:5000/cars/${carId}`, {
    method: 'DELETE'
  });
  return response.json();
};
```

### Get Car Images
```javascript
const getCarImages = async (carId) => {
  const response = await fetch(`http://localhost:5000/cars/${carId}/images`);
  const result = await response.json();
  if (result.status === 'success') {
    return result.data;
  }
  return [];
};
```

### Upload Image
```javascript
const uploadImage = async (carId, imageFile) => {
  const formData = new FormData();
  formData.append('image', imageFile);
  
  const response = await fetch(`http://localhost:5000/cars/${carId}/images`, {
    method: 'POST',
    body: formData
  });
  return response.json();
};

// Usage with file input
document.getElementById('imageInput').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  const result = await uploadImage(1, file);
  if (result.status === 'success') {
    console.log('Image uploaded:', result.data.picid);
  }
});
```

### Delete Image
```javascript
const deleteImage = async (carId, picId) => {
  const response = await fetch(`http://localhost:5000/cars/${carId}/images/${picId}`, {
    method: 'DELETE'
  });
  return response.json();
};
```

### Set Main Image
```javascript
const setMainImage = async (carId, picId) => {
  const response = await fetch(`http://localhost:5000/cars/${carId}/images/${picId}/main`, {
    method: 'PUT'
  });
  return response.json();
};
```

---

## React Hook Examples

### Using State to Manage Cars
```javascript
import { useState, useEffect } from 'react';

function CarsComponent() {
  const [cars, setCars] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCars = async () => {
      try {
        const response = await fetch('http://localhost:5000/cars');
        const result = await response.json();
        if (result.status === 'success') {
          setCars(result.data);
        }
      } catch (error) {
        console.error('Failed to fetch cars:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCars();
  }, []);

  if (loading) return <div>Loading...</div>;
  
  return (
    <div>
      {cars.map(car => (
        <div key={car.carid}>
          <h3>{car.year} {car.make} {car.model}</h3>
          <p>Price: ${car.price}</p>
        </div>
      ))}
    </div>
  );
}
```

### Form Submission for Adding Car
```javascript
function AddCarForm() {
  const [formData, setFormData] = useState({
    make: '',
    model: '',
    trim: '',
    year: new Date().getFullYear(),
    miles: 0,
    price: 0,
    vin: '',
    status: 'available',
    description: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:5000/cars', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const result = await response.json();
      if (result.status === 'success') {
        alert('Car added successfully!');
        setFormData({ /* reset */ });
      } else {
        alert(`Error: ${result.message}`);
      }
    } catch (error) {
      alert(`Failed to add car: ${error.message}`);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="make" value={formData.make} onChange={handleChange} required />
      <input name="model" value={formData.model} onChange={handleChange} required />
      {/* other fields */}
      <button type="submit">Add Car</button>
    </form>
  );
}
```

---

## PHP vs Flask Comparison

| Operation | PHP Endpoint | Flask Endpoint | Method | Notes |
|-----------|---------|---------|--------|-------|
| Register | `/api/register.php` | `/register` | POST | Same request/response |
| Login | `/api/login.php` | `/login` | POST | Returns JWT token |
| List Cars | `/api/get_cars.php` | `/cars` | GET | Includes main image URL |
| Get Car | `/api/get_car_by_id.php?id=1` | `/cars/1` | GET | RESTful path param |
| Add Car | `/api/add_car.php` | `/cars` | POST | JSON body instead of form |
| Update Car | `/api/update_car.php` | `/cars/1` | PUT | RESTful path param |
| Delete Car | `/api/delete_car.php` | `/cars/1` | DELETE | RESTful method |
| List Images | `/api/get_car_images.php?carid=1` | `/cars/1/images` | GET | RESTful path |
| Upload Image | `/api/add_single_image.php` | `/cars/1/images` | POST | FormData upload |
| Delete Image | `/api/delete_image.php` | `/cars/1/images/5` | DELETE | RESTful path |
| Set Main | `/api/set_is_main.php` | `/cars/1/images/5/main` | PUT | RESTful nested resource |

---

## Error Handling Best Practices

```javascript
const fetchWithErrorHandling = async (url, options = {}) => {
  try {
    const response = await fetch(url, options);
    
    if (response.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem('authToken');
      window.location.href = '/login';
      return null;
    }
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.message || `HTTP ${response.status}`);
    }
    
    return data;
  } catch (error) {
    console.error(`API Error: ${error.message}`);
    throw error;
  }
};

// Usage
try {
  const result = await fetchWithErrorHandling('http://localhost:5000/cars');
  console.log(result.data);
} catch (error) {
  // Handle error
}
```

---

## Token Management (JWT)

```javascript
// Store token after login
const loginAndStore = async (email, password) => {
  const response = await fetch('http://localhost:5000/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  const data = await response.json();
  
  if (data.status === 'success') {
    localStorage.setItem('authToken', data.token);
    return true;
  }
  return false;
};

// Retrieve and use token in headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('authToken');
  return {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` })
  };
};

// Use in requests
const authenticatedFetch = (url, options = {}) => {
  return fetch(url, {
    ...options,
    headers: getAuthHeaders()
  });
};
```
