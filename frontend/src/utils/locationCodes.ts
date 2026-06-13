import type { LocationNode, LocationNodeType } from "../types/api";

const typePrefixes: Record<LocationNodeType, string> = {
  HOME: "H",
  FLOOR: "FL",
  ROOM: "R",
  ZONE: "A",
  FURNITURE: "F",
  COMPARTMENT: "C",
  BOX: "B",
  CUSTOM: "X"
};

export function inferChildNodeType(parent: LocationNode | null): LocationNodeType {
  if (!parent) {
    return "ROOM";
  }

  if (parent.node_type === "ROOM") {
    return "FURNITURE";
  }

  if (parent.node_type === "FURNITURE") {
    return "COMPARTMENT";
  }

  return "CUSTOM";
}

export function nextLocationCode(
  nodes: LocationNode[],
  parentId: number | null,
  nodeType: LocationNodeType
) {
  const siblingCodes = new Set(
    nodes
      .filter((node) => (node.parent ?? null) === parentId)
      .map((node) => node.code.toUpperCase())
  );

  const prefix = typePrefixes[nodeType] ?? "X";
  let number = 1;
  let code = `${prefix}${number}`;

  while (siblingCodes.has(code.toUpperCase())) {
    number += 1;
    code = `${prefix}${number}`;
  }

  return code;
}
