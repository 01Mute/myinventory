import type { LocationNode, TreeNode } from "../types/api";

export function buildLocationTree(nodes: LocationNode[]) {
  const byId = new Map<number, TreeNode>();
  const roots: TreeNode[] = [];

  nodes.forEach((node) => {
    byId.set(node.id, { ...node, children: [] });
  });

  byId.forEach((node) => {
    if (node.parent && byId.has(node.parent)) {
      byId.get(node.parent)?.children.push(node);
      return;
    }
    roots.push(node);
  });

  const sortNodes = (items: TreeNode[]) => {
    items.sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name));
    items.forEach((item) => sortNodes(item.children));
  };

  sortNodes(roots);
  return roots;
}

export function flattenLocationTree(nodes: TreeNode[]) {
  const flat: TreeNode[] = [];

  const visit = (node: TreeNode) => {
    flat.push(node);
    node.children.forEach(visit);
  };

  nodes.forEach(visit);
  return flat;
}
