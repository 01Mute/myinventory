import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import type { TreeNode } from "../types/api";

export function LocationPicker({
  emptyLabel,
  expandedIds,
  selectedId,
  tree,
  onSelect,
  onToggle
}: {
  emptyLabel: string;
  expandedIds: Set<number>;
  selectedId: string;
  tree: TreeNode[];
  onSelect: (locationId: string) => void;
  onToggle: (nodeId: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const selectedNode = findTreeNode(tree, selectedId);

  // Without this the dropdown stayed open until something inside it was
  // clicked, overlapping the rest of the form.
  useEffect(() => {
    if (!open) {
      return;
    }

    function handlePointerDown(event: globalThis.PointerEvent) {
      const target = event.target;
      if (target instanceof Node && containerRef.current?.contains(target)) {
        return;
      }
      setOpen(false);
    }

    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div className="location-dropdown" ref={containerRef}>
      <button
        className="location-dropdown-trigger"
        type="button"
        onClick={() => setOpen((current) => !current)}
      >
        <span>{selectedNode ? selectedNode.path : emptyLabel}</span>
        <ChevronDown aria-hidden="true" />
      </button>
      {open ? (
        <div className="location-picker" role="listbox">
          <button
            className={`location-picker-row ${selectedId ? "" : "selected"}`}
            type="button"
            onClick={() => {
              onSelect("");
              setOpen(false);
            }}
          >
            <span className="location-toggle-spacer" />
            <span>{emptyLabel}</span>
            <strong />
          </button>
          {tree.map((node) => (
            <LocationPickerNode
              expandedIds={expandedIds}
              key={node.id}
              node={node}
              selectedId={selectedId}
              onSelect={(locationId, hasChildren) => {
                onSelect(locationId);
                if (!hasChildren) {
                  setOpen(false);
                }
              }}
              onToggle={onToggle}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function LocationPickerNode({
  expandedIds,
  node,
  selectedId,
  onSelect,
  onToggle
}: {
  expandedIds: Set<number>;
  node: TreeNode;
  selectedId: string;
  onSelect: (locationId: string, hasChildren: boolean) => void;
  onToggle: (nodeId: number) => void;
}) {
  const expanded = expandedIds.has(node.id);
  const hasChildren = node.children.length > 0;
  const ToggleIcon = expanded ? ChevronDown : ChevronRight;

  return (
    <>
      <div
        className={`location-picker-row ${selectedId === String(node.id) ? "selected" : ""}`}
        style={{ paddingLeft: `${node.level * 16 + 8}px` }}
      >
        {hasChildren ? (
          <button
            className="location-toggle"
            type="button"
            title={expanded ? "접기" : "펼치기"}
            onClick={(event) => {
              event.stopPropagation();
              onToggle(node.id);
            }}
          >
            <ToggleIcon aria-hidden="true" />
          </button>
        ) : (
          <span className="location-toggle-spacer" />
        )}
        <button
          className="location-picker-main"
          type="button"
          onClick={() => {
            if (hasChildren) {
              onToggle(node.id);
            }
            onSelect(String(node.id), hasChildren);
          }}
        >
          <span>{node.name}</span>
          <strong>{node.full_code}</strong>
        </button>
      </div>
      {expanded
        ? node.children.map((child) => (
            <LocationPickerNode
              expandedIds={expandedIds}
              key={child.id}
              node={child}
              selectedId={selectedId}
              onSelect={onSelect}
              onToggle={onToggle}
            />
          ))
        : null}
    </>
  );
}

function findTreeNode(nodes: TreeNode[], selectedId: string): TreeNode | null {
  if (!selectedId) {
    return null;
  }

  for (const node of nodes) {
    if (String(node.id) === selectedId) {
      return node;
    }
    const child = findTreeNode(node.children, selectedId);
    if (child) {
      return child;
    }
  }

  return null;
}
