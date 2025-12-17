
# 🌐 Semi-Automatic Georeferencing

**Semi-Automatic Georeferencing** is a streamlined tool designed to align raw imagery (**RAW**) with georeferenced base maps (**REF**) using a semi-automatic workflow. By combining algorithmic precision with user-guided anchors, it simplifies the process of spatial rectification.

## 🚀 Getting Started

Follow these steps to get the application running locally using Docker.

### 1. Build the Environment

Open your terminal in the project root and build the containers:

```bash
docker-compose build

```

### 2. Launch the Application

Start the services:

```bash
docker-compose up

```

### 3. Access the Interface

Once the containers are active, open your browser and navigate to:

> **[http://localhost:4173/](http://localhost:4173/)**

---

## 🛠 How It Works

The app utilizes a **RAW + REF** workflow to ensure maximum accuracy:

1. **Upload RAW Imagery:** Import the unreferenced image or scan that needs alignment.
2. **Select Reference (REF):** Choose your georeferenced base map or coordinate system.
3. **Semi-Auto Alignment:** The system suggests potential Ground Control Points (GCPs). You simply confirm or adjust them to finalize the georeferencing.
4. **Export:** Download your newly rectified spatial data.

## 📦 Requirements

* [Docker](https://www.docker.com/get-started)
* [Docker Compose](https://docs.docker.com/compose/install/)


