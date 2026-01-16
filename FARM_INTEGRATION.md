# Farm Backend Integration Guide

This document provides instructions for integrating the Farm frontend class with the backend API.

## Overview

The backend provides a complete REST API for managing farms, including:
- Farm creation and management
- Plant/crop management (planting, growing, harvesting)
- Animal management (feeding, breeding, product collection)
- Manager hiring/firing
- Storage management (transfer between farm and global storage)
- Timer updates for crops and animals

## API Endpoints

### Base URL
All endpoints are prefixed with `/api/farms`

### Authentication
All endpoints require a valid `username` in the URL path.

---

## Endpoints

### 1. Get All Farms
**GET** `/api/farms/<username>`

Get all farms owned by a user.

**Response:**
```json
{
  "farms": [
    {
      "id": "farm_id",
      "name": "My Farm",
      "farmType": "crop",
      "plants": [...],
      "animals": [...],
      "manager": {...},
      "moneyAccount": {...},
      "storage": {...}
    }
  ],
  "count": 1
}
```

---

### 2. Get Specific Farm
**GET** `/api/farms/<username>/<farm_id>`

Get details of a specific farm.

**Response:**
```json
{
  "farm": {
    "id": "farm_id",
    "name": "My Farm",
    ...
  }
}
```

---

### 3. Create Farm
**POST** `/api/farms/<username>/create`

Create a new farm.

**Request Body:**
```json
{
  "name": "My Farm",
  "farmType": "crop",  // or "cattle"
  "numberOfPlots": 10,
  "propertyId": "optional_property_id"
}
```

**Response:**
```json
{
  "message": "Farm created successfully",
  "farm": {...}
}
```

---

### 4. Save Farm
**POST** `/api/farms/<username>/<farm_id>/save`

Save farm state. This matches the frontend `save()` method.

**Request Body:**
```json
{
  // Full farm data dictionary (from toDict())
}
```

**Response:**
```json
{
  "message": "Farm saved successfully",
  "farm": {...}
}
```

---

### 5. Plant Seed
**POST** `/api/farms/<username>/<farm_id>/plant`

Plant a seed on a plot.

**Request Body:**
```json
{
  "plotNumber": 1,
  "seedType": "rice",
  "fromGlobalStorage": false,  // optional
  "globalStorage": {...}  // optional, required if fromGlobalStorage is true
}
```

**Response:**
```json
{
  "message": "Seed planted successfully",
  "farm": {...}
}
```

---

### 6. Harvest Plot
**POST** `/api/farms/<username>/<farm_id>/harvest`

Harvest produce from a plot.

**Request Body:**
```json
{
  "plotNumber": 1,
  "quantity": 1  // optional, default: 1
}
```

**Response:**
```json
{
  "message": "Plot harvested successfully",
  "farm": {...}
}
```

---

### 7. Add Animal
**POST** `/api/farms/<username>/<farm_id>/add-animal`

Add an animal to the farm.

**Request Body:**
```json
{
  "type": "cow",  // "cow", "chicken", "goat", "pig", "sheep"
  "birthDate": "2024-01-01T00:00:00"  // optional, ISO format
}
```

**Response:**
```json
{
  "message": "Animal added successfully",
  "farm": {...}
}
```

---

### 8. Feed Animal
**POST** `/api/farms/<username>/<farm_id>/feed-animal`

Feed an animal (required for production).

**Request Body:**
```json
{
  "animalId": "animal_123"
}
```

**Response:**
```json
{
  "message": "Animal fed successfully",
  "farm": {...}
}
```

---

### 9. Collect Products
**POST** `/api/farms/<username>/<farm_id>/collect-products`

Collect products from an animal.

**Request Body:**
```json
{
  "animalId": "animal_123"
}
```

**Response:**
```json
{
  "message": "Products collected successfully",
  "collectedProducts": [...],
  "farm": {...}
}
```

---

### 10. Hire Manager
**POST** `/api/farms/<username>/<farm_id>/hire-manager`

Hire a farm manager.

**Request Body:**
```json
{
  "id": "manager_123",
  "name": "John Doe",
  "salary": 1000,
  "automationLevel": 5
}
```

**Response:**
```json
{
  "message": "Manager hired successfully",
  "farm": {...}
}
```

---

### 11. Fire Manager
**POST** `/api/farms/<username>/<farm_id>/fire-manager`

Fire the current farm manager.

**Response:**
```json
{
  "message": "Manager fired successfully",
  "farm": {...}
}
```

---

### 12. Update Timers
**POST** `/api/farms/<username>/<farm_id>/update-timers`

Update farm timers (crops, animals, pregnancy).

**Request Body (optional):**
```json
{
  "currentGameDate": "2024-01-01T00:00:00"  // ISO format, optional (uses stored game date if not provided)
}
```

**Response:**
```json
{
  "message": "Timers updated successfully",
  "farm": {...}
}
```

---

### 13. Transfer Storage
**POST** `/api/farms/<username>/<farm_id>/transfer-storage`

Transfer items between farm storage and global storage.

**Request Body:**
```json
{
  "itemId": "item_123",
  "quantity": 5,
  "direction": "toGlobal",  // or "fromGlobal"
  "globalStorage": {...}  // required
}
```

**Response:**
```json
{
  "message": "Transfer completed successfully",
  "farm": {...}
}
```

---

### 14. Convert Seeds
**POST** `/api/farms/<username>/<farm_id>/convert-seeds`

Convert produce to seeds.

**Request Body:**
```json
{
  "produceType": "rice",
  "quantity": 20
}
```

**Response:**
```json
{
  "message": "Produce converted to seeds successfully",
  "farm": {...}
}
```

---

## Frontend Integration

### 1. Update Farm.save() Method

Modify the `save()` method in your Farm class to call the backend API:

```typescript
async save(username: string): Promise<Response> {
    // Option 1: Use farm ID in URL (recommended)
    const apiUrl = `/api/farms/${username}/${this.id}/save`;
    
    // Option 2: Use farm ID from body (also supported)
    // const apiUrl = `/api/farms/${username}/save`;
    
    const bodyData = this.toDict();
    
    const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(bodyData),
    });
    
    if (!response.ok) {
        throw new Error(`Failed to save farm: ${response.statusText}`);
    }
    
    const data = await response.json();
    // Optionally update local state with returned farm data
    this.load(data.farm);
    
    return response;
}
```

**Note:** The backend supports both URL patterns:
- `/api/farms/<username>/<farm_id>/save` (with farm_id in URL)
- `/api/farms/<username>/save` (with farm_id in request body)

### 2. Load Farm from Backend

Create a method to load farm from backend:

```typescript
static async loadFromBackend(username: string, farmId: string): Promise<Farm | null> {
    try {
        const response = await fetch(`/api/farms/${username}/${farmId}`);
        if (!response.ok) {
            return null;
        }
        
        const data = await response.json();
        const farm = new Farm(data.farm);
        return farm;
    } catch (error) {
        console.error('Error loading farm:', error);
        return null;
    }
}

static async loadAllFarms(username: string): Promise<Farm[]> {
    try {
        const response = await fetch(`/api/farms/${username}`);
        if (!response.ok) {
            return [];
        }
        
        const data = await response.json();
        return data.farms.map((farmData: FarmInterface) => new Farm(farmData));
    } catch (error) {
        console.error('Error loading farms:', error);
        return [];
    }
}
```

### 3. Update Method Calls

Update your Farm methods to call backend APIs when needed:

```typescript
async plantSeed(plotNumber: number, seedType: string, fromGlobalStorage: boolean = false, globalStorage?: { items: BusinessStorageItem[] }): Promise<boolean> {
    // Call backend API
    try {
        const response = await fetch(`/api/farms/${this.username}/${this.id}/plant`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                plotNumber,
                seedType,
                fromGlobalStorage,
                globalStorage,
            }),
        });
        
        if (!response.ok) {
            return false;
        }
        
        const data = await response.json();
        // Update local state with returned farm data
        this.load(data.farm);
        return true;
    } catch (error) {
        console.error('Error planting seed:', error);
        return false;
    }
}
```

### 4. Socket.IO Events

Listen for real-time updates from the backend:

```typescript
// In your Socket.IO setup
socket.on('farm_crops_ready', (data) => {
    // Handle crops ready event
    const { farm_id, payload } = data;
    // Update UI to show ready crops
});

socket.on('farm_animals_birth', (data) => {
    // Handle animal birth event
    const { farm_id, payload } = data;
    // Update UI to show new animals
});
```

### 5. Periodic Timer Updates

Set up periodic timer updates:

```typescript
// Update farm timers every minute (or as needed)
setInterval(async () => {
    for (const farm of this.farms) {
        try {
            await fetch(`/api/farms/${farm.username}/${farm.id}/update-timers`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
        } catch (error) {
            console.error('Error updating timers:', error);
        }
    }
}, 60000); // Every minute
```

Or use the background thread system which automatically updates farms.

---

## Data Format

### FarmPlant
```typescript
{
    id: string;
    plotNumber: number;
    produceType: string | null;
    produceId: string | null;
    plantedDate: string;  // ISO format
    harvestDate: string;   // ISO format
    status: 'idle' | 'planted' | 'growing' | 'ready' | 'harvested';
}
```

### Animal
```typescript
{
    id: string;
    type: string;  // 'cow', 'chicken', 'goat', 'pig', 'sheep'
    birthDate: string;  // ISO format
    expirationDate: string;  // ISO format
    isPregnant: boolean;
    pregnancyStartDate: string | null;  // ISO format
    birthCount: number;
    products: string[];
    lastFedDate: string | null;  // ISO format
    lastProductCollectionDate: string | null;  // ISO format
}
```

### Manager
```typescript
{
    id: string;
    name: string;
    salary: number;
    automationLevel: number;
    hiredDate: string;  // ISO format
}
```

---

## Error Handling

All endpoints return standard HTTP status codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request (validation errors)
- `403`: Forbidden (farm doesn't belong to user)
- `404`: Not Found
- `500`: Internal Server Error

Error responses follow this format:
```json
{
  "error": "Error message here"
}
```

---

## Notes

1. **Date Handling**: All dates are stored and transmitted in ISO 8601 format (e.g., `"2024-01-01T00:00:00"`).

2. **Storage Management**: Farm storage is separate from global player storage. Use transfer endpoints to move items between them.

3. **Timer Updates**: The backend has a background thread system that automatically updates farm timers. You can also manually trigger updates via the API.

4. **Game Date**: The backend maintains a global game date. If not provided in API calls, it uses the stored game date.

5. **Animal Types**: Supported animal types are: `cow`, `chicken`, `goat`, `pig`, `sheep`.

6. **Crop Types**: Supported crop types are: `rice`, `tomato`, `wheat`, `corn`, `potato`, `soybean`.

---

## Example Usage

```typescript
// Create a farm
const farm = Farm.createFarm('My Farm', 'crop', 10, undefined, 'username');
const response = await fetch('/api/farms/username/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        name: 'My Farm',
        farmType: 'crop',
        numberOfPlots: 10,
    }),
});
const data = await response.json();
farm.id = data.farm.id;

// Plant a seed
await farm.plantSeed(1, 'rice');

// Harvest when ready
await farm.harvestPlot(1);

// Add an animal
farm.addAnimal('cow');

// Feed animal
farm.feedAnimal(animalId);

// Collect products
const products = farm.collectProducts(animalId);
```

---

## Background Timer System

The backend includes a background timer system that automatically updates farms. To trigger updates for a specific user's farms:

```python
# In your backend code
from app.BackgroundThreads import bg_update_farm_timers
import threading

# Update all farms for a user
thread = threading.Thread(
    target=bg_update_farm_timers,
    args=('username',),
    daemon=True
)
thread.start()
```

The background system will:
- Update crop growth statuses
- Check animal pregnancies and process births
- Check for expired animals
- Emit Socket.IO events when crops are ready or animals give birth
