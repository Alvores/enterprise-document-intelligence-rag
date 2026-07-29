# 1. The Virtual Private Cloud (VPC)
resource "google_compute_network" "vpc_network" {
  name                    = "rag-vpc-network"
  project                 = var.project_id
  auto_create_subnetworks = false # Custom subnets provide tighter security
  routing_mode            = "REGIONAL"
}

# 2. Serverless Subnet for Cloud Run Direct VPC Egress
resource "google_compute_subnetwork" "serverless_subnet" {
  name          = "rag-serverless-subnet"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.vpc_network.id
  ip_cidr_range = "10.124.0.0/24" # Small subnet specifically for Cloud Run instances
}

# 3. Private IP Allocation for the Database Network
# Allocates a block of internal IP addresses specifically for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "rag-private-ip-address"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 24
  network       = google_compute_network.vpc_network.id
}

# 4. Private Service Connect (VPC Peering)
# Bridges the allocated IP block to Google's internal Cloud SQL service network
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}