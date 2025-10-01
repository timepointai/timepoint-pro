import sys
import json
from pathlib import Path

def inspect_entity_knowledge(sim, entity_id, output_dir):
    """Deep inspection of entity knowledge"""
    entity = sim.entities.get(entity_id)
    if not entity:
        return None
    
    inspection = {
        "entity_id": entity_id,
        "resolution": entity.resolution.value if hasattr(entity, 'resolution') else "unknown",
        "knowledge_count": len(entity.knowledge) if hasattr(entity, 'knowledge') else 0,
        "knowledge_items": []
    }
    
    # Extract actual knowledge content
    if hasattr(entity, 'knowledge'):
        for idx, knowledge_item in enumerate(entity.knowledge):
            item_data = {
                "index": idx,
                "type": type(knowledge_item).__name__,
            }
            
            # Try to extract meaningful content
            if hasattr(knowledge_item, '__dict__'):
                item_data["attributes"] = {
                    k: str(v)[:200] if len(str(v)) > 200 else str(v)
                    for k, v in knowledge_item.__dict__.items()
                    if not k.startswith('_')
                }
            else:
                item_data["content"] = str(knowledge_item)[:500]
            
            inspection["knowledge_items"].append(item_data)
    
    # Check for graph structure
    if hasattr(entity, 'knowledge_graph'):
        inspection["has_knowledge_graph"] = True
        inspection["graph_node_count"] = len(entity.knowledge_graph.nodes) if hasattr(entity.knowledge_graph, 'nodes') else 0
    else:
        inspection["has_knowledge_graph"] = False
    
    return inspection

def dump_all_knowledge(sim, output_file):
    """Dump all entity knowledge to file"""
    output_dir = Path(output_file).parent
    all_knowledge = {}
    
    for entity_id in sim.entities.keys():
        all_knowledge[entity_id] = inspect_entity_knowledge(sim, entity_id, output_dir)
    
    with open(output_file, 'w') as f:
        json.dump(all_knowledge, f, indent=2)
    
    print(f"\n📊 Knowledge dump saved to: {output_file}")
    return all_knowledge

def print_knowledge_summary(knowledge_data):
    """Print readable summary of knowledge"""
    print("\n" + "="*70)
    print("KNOWLEDGE SUMMARY")
    print("="*70)
    
    for entity_id, data in knowledge_data.items():
        if data:
            print(f"\n{entity_id}:")
            print(f"  Resolution: {data['resolution']}")
            print(f"  Knowledge items: {data['knowledge_count']}")
            print(f"  Has graph: {data.get('has_knowledge_graph', False)}")
            
            if data['knowledge_items']:
                print(f"  Sample items:")
                for item in data['knowledge_items'][:3]:  # Show first 3
                    print(f"    [{item['index']}] {item['type']}")
                    if 'attributes' in item:
                        for k, v in list(item['attributes'].items())[:2]:
                            print(f"        {k}: {v[:100]}...")
    print("="*70)

def capture_entity_state(sim, timepoint_id, output_dir):
    """Capture complete entity states at a timepoint"""
    state = {
        "timepoint_id": timepoint_id,
        "entities": {}
    }
    
    for entity_id, entity in sim.entities.items():
        entity_state = {
            "resolution": entity.resolution.value if hasattr(entity, 'resolution') else "unknown",
            "knowledge_count": len(entity.knowledge) if hasattr(entity, 'knowledge') else 0,
            "query_count": getattr(entity, 'query_count', 0),
        }
        
        # Capture latest knowledge
        if hasattr(entity, 'knowledge') and entity.knowledge:
            latest = entity.knowledge[-1]
            entity_state["latest_knowledge"] = {
                "type": type(latest).__name__,
                "content_preview": str(latest)[:300]
            }
        
        state["entities"][entity_id] = entity_state
    
    return state

if __name__ == "__main__":
    # This will be called from the main script
    pass
