#!/usr/bin/env python3
"""
Fixed MCP Mesh Network Example
Demonstrates distributed AI training using browser-native chuk-mcp
"""

import asyncio
import json
import time
import uuid
import hashlib
import random
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PeerInfo:
    """Information about a peer node in the mesh"""
    node_id: str
    address: str
    port: int
    compute_power: float  # TFLOPS
    last_seen: datetime
    capabilities: List[str]
    reputation: float = 1.0
    total_contributions: int = 0

class MeshCoordinator:
    """Manages peer discovery, connection, and network topology"""
    
    def __init__(self):
        self.node_id = str(uuid.uuid4())[:8]
        self.peers: Dict[str, PeerInfo] = {}
        self.pending_connections: Set[str] = set()
        self.network_topology: Dict[str, List[str]] = {}
        self.heartbeat_interval = 30
        self.max_peers = 50
        
    async def discover_peers(self, max_peers: int = 10) -> Dict[str, Any]:
        """Discover and connect to peer nodes in the mesh network"""
        try:
            logger.info(f"Starting peer discovery for node {self.node_id}")
            
            # Simulate discovering peers
            discovered_peers = []
            for i in range(max_peers):
                peer_info = {
                    "node_id": f"peer_{uuid.uuid4().hex[:8]}",
                    "address": f"192.168.1.{100 + i}",
                    "port": 8080,
                    "compute_power": round(random.uniform(0.5, 3.0), 2),
                    "last_seen": datetime.now(),
                    "capabilities": ["training", "inference"],
                    "reputation": round(random.uniform(0.8, 1.0), 3)
                }
                discovered_peers.append(peer_info)
            
            # Connect to peers
            connected_peers = []
            for peer_info in discovered_peers:
                # Simulate connection (90% success rate)
                if random.random() > 0.1:
                    peer = PeerInfo(**peer_info)
                    self.peers[peer.node_id] = peer
                    connected_peers.append(peer_info)
                    logger.info(f"Connected to peer {peer.node_id} with {peer.compute_power} TFLOPS")
            
            logger.info(f"Discovery complete: {len(connected_peers)} peers connected")
            
            return {
                "node_id": self.node_id,
                "discovered": len(discovered_peers),
                "connected": len(connected_peers),
                "total_peers": len(self.peers),
                "network_health": self._calculate_network_health(),
                "peers": [asdict(peer) for peer in self.peers.values()]
            }
            
        except Exception as e:
            logger.error(f"Peer discovery failed: {e}")
            return {"error": f"Peer discovery failed: {str(e)}"}
    
    def _calculate_network_health(self) -> float:
        """Calculate overall network health score"""
        if not self.peers:
            return 0.0
        
        avg_reputation = sum(peer.reputation for peer in self.peers.values()) / len(self.peers)
        connectivity_score = min(len(self.peers) / self.max_peers, 1.0)
        return round((avg_reputation + connectivity_score) / 2, 3)

class GradientSharer:
    """Distributes training updates across the mesh network"""
    
    def __init__(self, mesh_coordinator: MeshCoordinator):
        self.coordinator = mesh_coordinator
        self.gradient_buffer: Dict[str, List[Dict]] = {}
        self.aggregation_strategy = "federated_averaging"
        
    async def share_gradients(self, task_id: str, gradients: Dict[str, Any], 
                            epoch: int, batch_id: str, loss: float, accuracy: float) -> Dict[str, Any]:
        """Share gradient updates with peer nodes"""
        try:
            logger.info(f"Sharing gradients for task {task_id}, epoch {epoch}")
            
            # Create gradient update
            gradient_update = {
                "task_id": task_id,
                "node_id": self.coordinator.node_id,
                "epoch": epoch,
                "batch_id": batch_id,
                "gradients": gradients,
                "loss": loss,
                "accuracy": accuracy,
                "timestamp": datetime.now().isoformat()
            }
            
            # Simulate compression
            original_size = len(str(gradients))
            compressed_size = int(original_size * 0.3)  # 70% compression
            compression_ratio = compressed_size / original_size
            
            # Broadcast to peers
            broadcast_results = []
            successful_broadcasts = 0
            
            for peer_id in self.coordinator.peers:
                try:
                    # Simulate network transmission (95% success rate)
                    if random.random() > 0.05:
                        transmission_time = round(random.uniform(0.1, 1.0), 3)
                        broadcast_results.append({
                            "peer_id": peer_id,
                            "status": "success",
                            "transmission_time": transmission_time
                        })
                        successful_broadcasts += 1
                        logger.debug(f"Sent gradients to peer {peer_id} in {transmission_time}s")
                    else:
                        broadcast_results.append({
                            "peer_id": peer_id,
                            "status": "failed",
                            "error": "Network timeout"
                        })
                except Exception as e:
                    broadcast_results.append({
                        "peer_id": peer_id,
                        "status": "failed",
                        "error": str(e)
                    })
            
            # Store in local buffer
            if task_id not in self.gradient_buffer:
                self.gradient_buffer[task_id] = []
            self.gradient_buffer[task_id].append(gradient_update)
            
            total_peers = len(self.coordinator.peers)
            success_rate = successful_broadcasts / max(total_peers, 1)
            
            logger.info(f"Gradient sharing complete: {successful_broadcasts}/{total_peers} peers reached")
            
            return {
                "gradient_id": f"{task_id}_{epoch}_{batch_id}",
                "compression_ratio": round(compression_ratio, 3),
                "peers_reached": successful_broadcasts,
                "total_peers": total_peers,
                "broadcast_success_rate": round(success_rate, 3),
                "transmission_details": broadcast_results,
                "buffer_size": len(self.gradient_buffer.get(task_id, []))
            }
            
        except Exception as e:
            logger.error(f"Gradient sharing failed: {e}")
            return {"error": f"Gradient sharing failed: {str(e)}"}
    
    async def collect_gradients(self, task_id: str, epoch: int, 
                              timeout_seconds: int = 30) -> Dict[str, Any]:
        """Collect gradient updates from peer nodes for aggregation"""
        try:
            logger.info(f"Collecting gradients for task {task_id}, epoch {epoch}")
            
            start_time = time.time()
            collected_gradients = []
            
            # Simulate receiving gradients from peers
            for peer_id in self.coordinator.peers:
                # 80% chance each peer sends gradients
                if random.random() > 0.2:
                    simulated_gradient = {
                        "task_id": task_id,
                        "node_id": peer_id,
                        "epoch": epoch,
                        "batch_id": f"batch_{uuid.uuid4().hex[:8]}",
                        "gradients": {
                            "layer1": [random.gauss(0, 0.1) for _ in range(10)],
                            "layer2": [random.gauss(0, 0.1) for _ in range(5)]
                        },
                        "loss": round(random.uniform(0.1, 2.0), 4),
                        "accuracy": round(random.uniform(0.6, 0.95), 4),
                        "timestamp": datetime.now().isoformat()
                    }
                    collected_gradients.append(simulated_gradient)
                    logger.debug(f"Received gradients from peer {peer_id}")
            
            # Validate gradients
            valid_gradients = []
            validation_results = []
            
            for gradient in collected_gradients:
                # Simple validation
                is_valid = (
                    isinstance(gradient.get("gradients"), dict) and
                    len(str(gradient["gradients"])) < 1000000 and  # Size check
                    gradient.get("node_id") in self.coordinator.peers
                )
                
                validation_results.append({
                    "gradient_id": f"{gradient['task_id']}_{gradient['epoch']}_{gradient['batch_id']}",
                    "valid": is_valid,
                    "confidence": round(random.uniform(0.8, 1.0) if is_valid else random.uniform(0.1, 0.5), 3)
                })
                
                if is_valid:
                    valid_gradients.append(gradient)
            
            collection_time = round(time.time() - start_time, 2)
            
            logger.info(f"Gradient collection complete: {len(valid_gradients)}/{len(collected_gradients)} valid")
            
            return {
                "task_id": task_id,
                "epoch": epoch,
                "collection_time": collection_time,
                "gradients_received": len(collected_gradients),
                "gradients_valid": len(valid_gradients),
                "validation_success_rate": round(len(valid_gradients) / max(len(collected_gradients), 1), 3),
                "aggregation_successful": len(valid_gradients) > 0,
                "aggregated_gradient_hash": hashlib.md5(str(valid_gradients).encode()).hexdigest()[:16] if valid_gradients else None,
                "validation_details": validation_results
            }
            
        except Exception as e:
            logger.error(f"Gradient collection failed: {e}")
            return {"error": f"Gradient collection failed: {str(e)}"}

class ModelSyncer:
    """Keeps models consistent across the mesh network"""
    
    def __init__(self, mesh_coordinator: MeshCoordinator):
        self.coordinator = mesh_coordinator
        self.model_registry: Dict[str, Dict] = {}
        self.sync_strategy = "eventual_consistency"
        
    async def sync_model(self, model_name: str, model_weights: Dict[str, Any], 
                        metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Synchronize model across the mesh network"""
        try:
            logger.info(f"Syncing model {model_name} across mesh network")
            
            # Create model checkpoint
            weights_hash = hashlib.sha256(str(model_weights).encode()).hexdigest()[:16]
            current_version = len(self.model_registry.get(model_name, {})) + 1
            
            checkpoint = {
                "model_name": model_name,
                "version": current_version,
                "weights_hash": weights_hash,
                "metadata": metadata or {},
                "created_by": self.coordinator.node_id,
                "created_at": datetime.now().isoformat(),
                "size_bytes": len(str(model_weights))
            }
            
            # Store locally
            if model_name not in self.model_registry:
                self.model_registry[model_name] = {}
            self.model_registry[model_name][current_version] = checkpoint
            
            # Propagate to peers
            propagation_results = []
            successful_syncs = 0
            
            for peer_id in self.coordinator.peers:
                try:
                    # Simulate model propagation (90% success rate)
                    if random.random() > 0.1:
                        sync_time = round(random.uniform(1.0, 5.0), 2)
                        propagation_results.append({
                            "peer_id": peer_id,
                            "status": "success",
                            "sync_time": sync_time,
                            "version_accepted": current_version
                        })
                        successful_syncs += 1
                        logger.debug(f"Synced model to peer {peer_id} in {sync_time}s")
                    else:
                        propagation_results.append({
                            "peer_id": peer_id,
                            "status": "failed",
                            "error": "Sync timeout"
                        })
                except Exception as e:
                    propagation_results.append({
                        "peer_id": peer_id,
                        "status": "failed",
                        "error": str(e)
                    })
            
            total_peers = len(self.coordinator.peers)
            sync_success_rate = successful_syncs / max(total_peers, 1)
            
            logger.info(f"Model sync complete: {successful_syncs}/{total_peers} peers updated")
            
            return {
                "model_name": model_name,
                "version": current_version,
                "weights_hash": weights_hash,
                "sync_timestamp": checkpoint["created_at"],
                "peers_synced": successful_syncs,
                "total_peers": total_peers,
                "sync_success_rate": round(sync_success_rate, 3),
                "conflicts_detected": 0,  # Simplified for demo
                "propagation_details": propagation_results,
                "model_size_mb": round(checkpoint["size_bytes"] / 1024 / 1024, 2)
            }
            
        except Exception as e:
            logger.error(f"Model sync failed: {e}")
            return {"error": f"Model sync failed: {str(e)}"}

class ComputeAllocator:
    """Optimizes resource usage across the mesh network"""
    
    def __init__(self, mesh_coordinator: MeshCoordinator):
        self.coordinator = mesh_coordinator
        self.allocation_strategy = "fair_share"
        self.resource_pool = {}
        
    async def allocate_resources(self, task_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate computational resources for a distributed task"""
        try:
            task_id = str(uuid.uuid4())[:8]
            logger.info(f"Allocating resources for task {task_id}")
            
            # Extract requirements
            required_compute = task_requirements.get("compute_tflops", 1.0)
            required_memory = task_requirements.get("memory_gb", 4.0)
            required_duration = task_requirements.get("duration_minutes", 60)
            task_priority = task_requirements.get("priority", "normal")
            
            # Check if we have any peers
            if not self.coordinator.peers:
                logger.warning("No peers available for resource allocation")
                return {
                    "task_id": task_id,
                    "allocation_successful": False,
                    "total_compute_allocated": 0.0,
                    "total_memory_allocated": 0.0,
                    "nodes_allocated": 0,
                    "allocation_efficiency": 0.0,
                    "error": "No peers available in network"
                }
            
            # Calculate available resources
            total_available_compute = sum(peer.compute_power for peer in self.coordinator.peers.values())
            logger.info(f"Total available compute: {total_available_compute} TFLOPS")
            
            # Create allocation plan
            allocations = []
            allocated_compute = 0.0
            allocated_memory = 0.0
            
            if self.allocation_strategy == "fair_share":
                # Distribute evenly across available nodes
                nodes_to_use = min(len(self.coordinator.peers), max(1, int(required_compute)))
                compute_per_node = required_compute / nodes_to_use
                memory_per_node = required_memory / nodes_to_use
                
                # Sort peers by compute power
                sorted_peers = sorted(self.coordinator.peers.values(), 
                                    key=lambda p: p.compute_power, reverse=True)
                
                for i, peer in enumerate(sorted_peers[:nodes_to_use]):
                    # Allocate up to 80% of peer's compute power
                    max_allocatable = peer.compute_power * 0.8
                    actual_compute = min(compute_per_node, max_allocatable)
                    actual_memory = min(memory_per_node, 32.0)  # Assume 32GB max per node
                    
                    if actual_compute > 0:
                        allocations.append({
                            "node_id": peer.node_id,
                            "allocated_compute": round(actual_compute, 2),
                            "allocated_memory": round(actual_memory, 1),
                            "utilization_increase": actual_compute / peer.compute_power
                        })
                        
                        allocated_compute += actual_compute
                        allocated_memory += actual_memory
                        logger.debug(f"Allocated {actual_compute} TFLOPS to peer {peer.node_id}")
            
            # Reserve resources on selected nodes
            reservation_results = []
            successful_reservations = 0
            
            for allocation in allocations:
                try:
                    # Simulate resource reservation (95% success rate)
                    if random.random() > 0.05:
                        reservation_id = str(uuid.uuid4())[:8]
                        reservation_results.append({
                            "node_id": allocation["node_id"],
                            "status": "reserved",
                            "reservation_id": reservation_id,
                            "compute_allocated": allocation["allocated_compute"],
                            "memory_allocated": allocation["allocated_memory"]
                        })
                        successful_reservations += 1
                    else:
                        reservation_results.append({
                            "node_id": allocation["node_id"],
                            "status": "failed",
                            "error": "Reservation timeout"
                        })
                except Exception as e:
                    reservation_results.append({
                        "node_id": allocation["node_id"],
                        "status": "failed",
                        "error": str(e)
                    })
            
            # Calculate final allocation metrics
            final_compute = sum(r["compute_allocated"] for r in reservation_results if r["status"] == "reserved")
            final_memory = sum(r["memory_allocated"] for r in reservation_results if r["status"] == "reserved")
            allocation_efficiency = final_compute / required_compute if required_compute > 0 else 0
            
            logger.info(f"Resource allocation complete: {final_compute} TFLOPS allocated across {successful_reservations} nodes")
            
            return {
                "task_id": task_id,
                "allocation_successful": successful_reservations > 0,
                "total_compute_allocated": round(final_compute, 2),
                "total_memory_allocated": round(final_memory, 2),
                "nodes_allocated": successful_reservations,
                "allocation_efficiency": round(allocation_efficiency, 3),
                "estimated_performance": {
                    "throughput_tflops": final_compute,
                    "parallelization_efficiency": min(1.0, final_compute / required_compute),
                    "estimated_completion_time_minutes": round(required_duration * (required_compute / final_compute), 1) if final_compute > 0 else float('inf')
                },
                "resource_reservations": reservation_results,
                "allocation_strategy": self.allocation_strategy
            }
            
        except Exception as e:
            logger.error(f"Resource allocation failed: {e}")
            return {"error": f"Resource allocation failed: {str(e)}"}

async def demo_mesh_training():
    """
    Demonstrate distributed AI training using mesh network tools
    """
    print("🌍 Initializing Distributed AI Mesh Network Demo")
    print("=" * 60)
    
    # Initialize components
    coordinator = MeshCoordinator()
    gradient_sharer = GradientSharer(coordinator)
    model_syncer = ModelSyncer(coordinator)
    allocator = ComputeAllocator(coordinator)
    
    try:
        # 1. Discover and connect to peers
        print("\n📡 Phase 1: Discovering peer nodes...")
        discovery_result = await coordinator.discover_peers(max_peers=5)
        
        if "error" in discovery_result:
            print(f"❌ Discovery failed: {discovery_result['error']}")
            return
        
        print(f"✅ Connected to {discovery_result['connected']} peers")
        print(f"   Network health: {discovery_result['network_health']}")
        
        # Display peer information
        for peer in discovery_result['peers']:
            print(f"   🖥️  Peer {peer['node_id']}: {peer['compute_power']} TFLOPS")
        
        # 2. Allocate resources for training
        print("\n⚡ Phase 2: Allocating compute resources...")
        allocation_result = await allocator.allocate_resources({
            "compute_tflops": 8.0,
            "memory_gb": 32.0,
            "duration_minutes": 120,
            "priority": "high"
        })
        
        if "error" in allocation_result:
            print(f"❌ Allocation failed: {allocation_result['error']}")
            return
        
        if not allocation_result['allocation_successful']:
            print(f"⚠️  Allocation partially failed: {allocation_result.get('error', 'Unknown reason')}")
            if allocation_result['total_compute_allocated'] == 0:
                print("❌ No compute resources allocated, cannot proceed with training")
                return
        
        print(f"✅ Allocated {allocation_result['total_compute_allocated']} TFLOPS across {allocation_result['nodes_allocated']} nodes")
        print(f"   Allocation efficiency: {allocation_result['allocation_efficiency']:.1%}")
        
        if allocation_result.get('estimated_performance'):
            perf = allocation_result['estimated_performance']
            print(f"   Estimated completion: {perf.get('estimated_completion_time_minutes', 'Unknown')} minutes")
        
        # 3. Simulate distributed training
        print("\n🧠 Phase 3: Starting distributed training...")
        task_id = "distributed_gpt_training"
        
        for epoch in range(3):
            print(f"\n📈 Epoch {epoch + 1}/3")
            
            # Create sample gradients
            gradients = {
                "embedding_layer": [random.gauss(0, 0.1) for _ in range(100)],
                "transformer_blocks": [[random.gauss(0, 0.1) for _ in range(50)] for _ in range(6)],
                "output_layer": [random.gauss(0, 0.1) for _ in range(10)]
            }
            
            # Share gradients
            share_result = await gradient_sharer.share_gradients(
                task_id=task_id,
                gradients=gradients,
                epoch=epoch + 1,
                batch_id=f"batch_{epoch}_001",
                loss=round(2.5 - epoch * 0.3, 4),
                accuracy=round(0.6 + epoch * 0.1, 4)
            )
            
            if "error" in share_result:
                print(f"   ❌ Gradient sharing failed: {share_result['error']}")
                continue
            
            print(f"   📤 Shared gradients to {share_result['peers_reached']}/{share_result['total_peers']} peers")
            print(f"      Compression ratio: {share_result['compression_ratio']:.1%}")
            print(f"      Success rate: {share_result['broadcast_success_rate']:.1%}")
            
            # Collect and aggregate gradients
            collect_result = await gradient_sharer.collect_gradients(
                task_id=task_id,
                epoch=epoch + 1,
                timeout_seconds=5  # Shorter timeout for demo
            )
            
            if "error" in collect_result:
                print(f"   ❌ Gradient collection failed: {collect_result['error']}")
                continue
            
            print(f"   📥 Collected {collect_result['gradients_received']} gradient updates")
            print(f"      Valid gradients: {collect_result['gradients_valid']}")
            print(f"      Validation success: {collect_result['validation_success_rate']:.1%}")
            
            # Sync updated model
            updated_model = {
                "embedding_weights": [[random.gauss(0, 0.1) for _ in range(128)] for _ in range(1000)],
                "transformer_weights": [[[random.gauss(0, 0.1) for _ in range(128)] for _ in range(128)] for _ in range(6)]
            }
            
            sync_result = await model_syncer.sync_model(
                model_name=f"gpt_model_epoch_{epoch + 1}",
                model_weights=updated_model,
                metadata={
                    "epoch": epoch + 1, 
                    "loss": 2.5 - epoch * 0.3,
                    "accuracy": 0.6 + epoch * 0.1,
                    "training_node": coordinator.node_id
                }
            )
            
            if "error" in sync_result:
                print(f"   ❌ Model sync failed: {sync_result['error']}")
                continue
            
            print(f"   🔄 Synced model to {sync_result['peers_synced']}/{sync_result['total_peers']} peers")
            print(f"      Model size: {sync_result['model_size_mb']:.1f} MB")
            print(f"      Sync success: {sync_result['sync_success_rate']:.1%}")
            
            # Brief pause between epochs
            await asyncio.sleep(1)
        
        # 4. Final network status
        print("\n📊 Phase 4: Final network status...")
        final_discovery = await coordinator.discover_peers(max_peers=0)  # Just get status
        
        if "error" not in final_discovery:
            print(f"✅ Network health: {final_discovery['network_health']}")
            print(f"✅ Total peers: {final_discovery['total_peers']}")
            
            total_compute = sum(peer['compute_power'] for peer in final_discovery['peers'])
            print(f"✅ Total network compute: {total_compute:.1f} TFLOPS")
        
        print("\n🎉 Distributed AI training demo completed successfully!")
        print("🌍 Your mesh network successfully coordinated AI training across multiple nodes!")
        print("🚀 This demonstrates the foundation for browser-native distributed AI!")
        
    except Exception as e:
        logger.error(f"Demo failed with exception: {e}")
        print(f"\n❌ Demo failed: {e}")
        print("Please check the logs for more details.")

if __name__ == "__main__":
    # Run the demo
    try:
        asyncio.run(demo_mesh_training())
    except KeyboardInterrupt:
        print("\n\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed to start: {e}")
        logger.error(f"Demo startup failed: {e}")