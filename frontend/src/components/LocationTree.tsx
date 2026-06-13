import { ChevronRight, MapPin } from "lucide-react";

import type { TreeNode } from "../types/api";

export function LocationTree({ nodes }: { nodes: TreeNode[] }) {
  return (
    <div className="tree-list">
      {nodes.map((node) => (
        <TreeItem key={node.id} node={node} />
      ))}
    </div>
  );
}

function TreeItem({ node }: { node: TreeNode }) {
  return (
    <div className="tree-item">
      <div className="tree-row" style={{ paddingLeft: `${node.level * 16}px` }}>
        {node.children.length > 0 ? <ChevronRight aria-hidden="true" /> : <MapPin aria-hidden="true" />}
        <span className="tree-name">{node.name}</span>
        <span className="tree-code">{node.full_code}</span>
        <span className="tree-type">{node.node_type}</span>
      </div>
      {node.children.map((child) => (
        <TreeItem key={child.id} node={child} />
      ))}
    </div>
  );
}
