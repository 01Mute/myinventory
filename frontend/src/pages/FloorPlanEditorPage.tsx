import { FormEvent, PointerEvent, WheelEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderOpen, Layers, Maximize2, Move, Pencil, Plus, Save, Square, Trash2 } from "lucide-react";
import { useParams } from "react-router-dom";

import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { IconButton } from "../components/IconButton";
import type {
  FloorPlan,
  Home,
  Item,
  LocationNode,
  LocationNodeType,
  RectGeometry,
  TreeNode
} from "../types/api";
import { buildLocationTree, flattenLocationTree } from "../utils/tree";
import {
  expandedSizeForRect,
  fallbackRect,
  normalizeRect,
  rectContains,
  rectForNode,
  snapRect
} from "../utils/geometry";
import { nextLocationCode } from "../utils/locationCodes";
import { readRecentFloorPlanId, saveRecentFloorPlanId } from "../utils/recentFloorPlan";

const editableTypes: LocationNodeType[] = ["ROOM", "FURNITURE"];
const CANVAS_EXPANSION_THRESHOLD = 10;

const nodeTypeLabels: Partial<Record<LocationNodeType, string>> = {
  ROOM: "방",
  FURNITURE: "가구",
  COMPARTMENT: "칸"
};

const palette: Record<LocationNodeType, { fill: string; stroke: string }> = {
  HOME: { fill: "#edf4f7", stroke: "#5b7d8c" },
  FLOOR: { fill: "#edf4f7", stroke: "#5b7d8c" },
  ROOM: { fill: "#e7f4ef", stroke: "#217a61" },
  ZONE: { fill: "#eef5fb", stroke: "#2f7da2" },
  FURNITURE: { fill: "#fff4d6", stroke: "#9b6a18" },
  COMPARTMENT: { fill: "#f1ecfb", stroke: "#7650a8" },
  BOX: { fill: "#fff0ea", stroke: "#b85b3d" },
  CUSTOM: { fill: "#f3f5f7", stroke: "#637480" }
};

const rectLimits: Record<
  "ROOM" | "FURNITURE",
  { minWidth: number; minHeight: number; maxWidth: number; maxHeight: number }
> = {
  ROOM: { minWidth: 80, minHeight: 60, maxWidth: 4000, maxHeight: 3000 },
  FURNITURE: { minWidth: 40, minHeight: 30, maxWidth: 1600, maxHeight: 1200 }
};

type PointerMode = "move" | "resize";

type DragState = {
  nodeId: number;
  mode: PointerMode;
  startX: number;
  startY: number;
  origin: RectGeometry;
  latest: RectGeometry;
  viewBox: CanvasViewBox;
};

type PanState = {
  startClientX: number;
  startClientY: number;
  originX: number;
  originY: number;
  viewBox: CanvasViewBox;
};

type DeleteLocationVariables = {
  id: number;
  deletedIds: number[];
  nextSelectedId: number | null;
};

type CanvasViewBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

function isDrawableType(nodeType: LocationNodeType) {
  return nodeType === "ROOM" || nodeType === "FURNITURE";
}

function isTypingTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  return (
    target.tagName === "INPUT" ||
    target.tagName === "TEXTAREA" ||
    target.tagName === "SELECT" ||
    target.isContentEditable
  );
}

function buildCanvasViewBox(
  floorPlan: FloorPlan | null,
  drawableLocations: LocationNode[],
  floorLocations: LocationNode[],
  geometryDrafts: Record<number, RectGeometry>
): CanvasViewBox {
  const padding = 220;
  const baseWidth = floorPlan?.width ?? 1000;
  const baseHeight = floorPlan?.height ?? 700;

  let minX = 0;
  let minY = 0;
  let maxX = baseWidth;
  let maxY = baseHeight;

  drawableLocations.forEach((node) => {
    const index = floorLocations.findIndex((location) => location.id === node.id);
    const rect = rectForNode(node, index >= 0 ? index : 0, geometryDrafts);
    const rectRight = rect.x + rect.width;
    const rectBottom = rect.y + rect.height;

    if (rect.x < -CANVAS_EXPANSION_THRESHOLD) {
      minX = Math.min(minX, rect.x);
    }
    if (rect.y < -CANVAS_EXPANSION_THRESHOLD) {
      minY = Math.min(minY, rect.y);
    }
    if (rectRight > baseWidth + CANVAS_EXPANSION_THRESHOLD) {
      maxX = Math.max(maxX, rectRight);
    }
    if (rectBottom > baseHeight + CANVAS_EXPANSION_THRESHOLD) {
      maxY = Math.max(maxY, rectBottom);
    }
  });

  return {
    x: Math.floor(minX - padding),
    y: Math.floor(minY - padding),
    width: Math.ceil(maxX - minX + padding * 2),
    height: Math.ceil(maxY - minY + padding * 2)
  };
}

function constrainRect(rect: RectGeometry, nodeType: LocationNodeType): RectGeometry {
  const normalized = normalizeRect(rect);
  if (nodeType !== "ROOM" && nodeType !== "FURNITURE") {
    return normalized;
  }

  const limits = rectLimits[nodeType];
  return {
    ...normalized,
    width: Math.min(limits.maxWidth, Math.max(limits.minWidth, normalized.width)),
    height: Math.min(limits.maxHeight, Math.max(limits.minHeight, normalized.height))
  };
}

export function FloorPlanEditorPage() {
  const { floorPlanId } = useParams();
  const queryClient = useQueryClient();
  const svgRef = useRef<SVGSVGElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const panRef = useRef<PanState | null>(null);

  const homesQuery = useQuery({ queryKey: ["homes"], queryFn: () => api.get<Home[]>("/homes/") });
  const floorPlansQuery = useQuery({
    queryKey: ["floor-plans"],
    queryFn: () => api.get<FloorPlan[]>("/floor-plans/")
  });
  const locationsQuery = useQuery({
    queryKey: ["location-nodes"],
    queryFn: () => api.get<LocationNode[]>("/location-nodes/")
  });

  const homes = homesQuery.data ?? [];
  const floorPlans = floorPlansQuery.data ?? [];
  const locations = locationsQuery.data ?? [];

  const [selectedHomeId, setSelectedHomeId] = useState("");
  const [selectedFloorPlanId, setSelectedFloorPlanId] = useState(
    () => floorPlanId ?? readRecentFloorPlanId()
  );
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [geometryDrafts, setGeometryDrafts] = useState<Record<number, RectGeometry>>({});
  const [detailForm, setDetailForm] = useState({
    node_type: "ROOM" as LocationNodeType,
    name: "",
    width: "160",
    height: "96"
  });
  const [stageZoom, setStageZoom] = useState(1);
  const [stagePan, setStagePan] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (floorPlanId) {
      setSelectedFloorPlanId(floorPlanId);
    }
  }, [floorPlanId]);

  useEffect(() => {
    if (!floorPlansQuery.isSuccess || !selectedFloorPlanId) {
      return;
    }
    if (!floorPlans.some((item) => String(item.id) === selectedFloorPlanId)) {
      setSelectedFloorPlanId("");
    }
  }, [floorPlans, floorPlansQuery.isSuccess, selectedFloorPlanId]);

  useEffect(() => {
    const floorPlan = floorPlans.find((item) => String(item.id) === selectedFloorPlanId);
    if (floorPlan) {
      setSelectedHomeId(String(floorPlan.home));
      return;
    }
    if (!selectedHomeId && homes.length > 0) {
      setSelectedHomeId(String(homes[0].id));
    }
  }, [floorPlans, homes, selectedFloorPlanId, selectedHomeId]);

  const visibleFloorPlans = useMemo(
    () => floorPlans.filter((floorPlan) => String(floorPlan.home) === selectedHomeId),
    [floorPlans, selectedHomeId]
  );

  useEffect(() => {
    const currentFloorPlanIsVisible = visibleFloorPlans.some(
      (floorPlan) => String(floorPlan.id) === selectedFloorPlanId
    );
    if (!currentFloorPlanIsVisible && visibleFloorPlans.length > 0) {
      const recentFloorPlanId = readRecentFloorPlanId();
      const nextFloorPlan =
        visibleFloorPlans.find((floorPlan) => String(floorPlan.id) === recentFloorPlanId) ??
        visibleFloorPlans[0];
      setSelectedFloorPlanId(String(nextFloorPlan.id));
    }
  }, [selectedFloorPlanId, visibleFloorPlans]);

  const selectedFloorPlan = floorPlans.find((item) => String(item.id) === selectedFloorPlanId) ?? null;

  useEffect(() => {
    if (selectedFloorPlan) {
      saveRecentFloorPlanId(selectedFloorPlan.id);
    }
  }, [selectedFloorPlan]);
  const floorLocations = useMemo(
    () => locations.filter((node) => String(node.floor_plan) === selectedFloorPlanId),
    [locations, selectedFloorPlanId]
  );
  const drawableLocations = useMemo(
    () => floorLocations.filter((node) => node.node_type === "ROOM" || node.node_type === "FURNITURE"),
    [floorLocations]
  );
  const sortedDrawableLocations = useMemo(
    () =>
      [...drawableLocations].sort((a, b) => {
        if (a.node_type === b.node_type) {
          return a.sort_order - b.sort_order || a.id - b.id;
        }
        return a.node_type === "ROOM" ? -1 : 1;
      }),
    [drawableLocations]
  );
  const tree = useMemo(() => buildLocationTree(floorLocations), [floorLocations]);
  const flatTree = useMemo(() => flattenLocationTree(tree), [tree]);
  const selectedNode = floorLocations.find((node) => node.id === selectedNodeId) ?? null;
  const selectedNodeIndex = selectedNode
    ? floorLocations.findIndex((node) => node.id === selectedNode.id)
    : -1;
  const selectedRect = useMemo(
    () =>
      selectedNode && selectedNodeIndex >= 0
        ? rectForNode(selectedNode, selectedNodeIndex, geometryDrafts)
        : null,
    [geometryDrafts, selectedNode, selectedNodeIndex]
  );
  const selectedNodeChildren = useMemo(
    () => floorLocations.filter((node) => node.parent === selectedNodeId),
    [floorLocations, selectedNodeId]
  );
  const selectedCompartments = useMemo(
    () => selectedNodeChildren.filter((node) => node.node_type === "COMPARTMENT"),
    [selectedNodeChildren]
  );
  const canvasViewBox = useMemo(
    () => buildCanvasViewBox(selectedFloorPlan, sortedDrawableLocations, floorLocations, geometryDrafts),
    [floorLocations, geometryDrafts, selectedFloorPlan, sortedDrawableLocations]
  );
  const viewportBox = useMemo(
    () => ({
      x: canvasViewBox.x + stagePan.x,
      y: canvasViewBox.y + stagePan.y,
      width: canvasViewBox.width / stageZoom,
      height: canvasViewBox.height / stageZoom
    }),
    [canvasViewBox, stagePan.x, stagePan.y, stageZoom]
  );

  const selectedItemsQuery = useQuery({
    queryKey: ["items", "location", selectedNodeId],
    queryFn: () => api.get<Item[]>(`/items/?location_node_id=${selectedNodeId}&include_children=true`),
    enabled: Boolean(selectedNodeId)
  });

  useEffect(() => {
    if (!selectedNode || !selectedRect) {
      return;
    }
    setDetailForm({
      node_type: selectedNode.node_type,
      name: selectedNode.name,
      width: String(Math.round(selectedRect.width)),
      height: String(Math.round(selectedRect.height))
    });
  }, [selectedNode, selectedRect]);

  const createNode = useMutation({
    mutationFn: async (nodeType: LocationNodeType = "ROOM") => {
      const index = drawableLocations.length;
      const rect = fallbackRect(index);
      const parentId = nodeType === "FURNITURE" ? findContainingRoomId(rect) : null;
      const node = await api.post<LocationNode>("/location-nodes/", {
        home: selectedFloorPlan?.home,
        floor_plan: selectedFloorPlan?.id,
        parent: parentId,
        node_type: nodeType,
        code: nextLocationCode(floorLocations, parentId, nodeType),
        name: nextDefaultNodeName(nodeType),
        geometry_json: rect,
        metadata_json: {}
      });
      return { node, rect };
    },
    onSuccess: ({ node, rect }) => {
      setSelectedNodeId(node.id);
      maybeExpandFloorPlan(rect);
      queryClient.invalidateQueries({ queryKey: ["location-nodes"] });
    }
  });

  const updateNode = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      api.patch<LocationNode>(`/location-nodes/${id}/`, payload),
    onSuccess: (node) => {
      setGeometryDrafts((current) => {
        const next = { ...current };
        delete next[node.id];
        return next;
      });
      queryClient.invalidateQueries({ queryKey: ["location-nodes"] });
    }
  });

  const updateFloorPlan = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      api.patch<FloorPlan>(`/floor-plans/${id}/`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["floor-plans"] });
    }
  });

  const deleteLocationNode = useMutation({
    mutationFn: async ({ id }: DeleteLocationVariables) => {
      await api.delete<null>(`/location-nodes/${id}/`);
    },
    onSuccess: (_data, variables) => {
      setSelectedNodeId(variables.nextSelectedId);
      setGeometryDrafts((current) => {
        const next = { ...current };
        variables.deletedIds.forEach((id) => {
          delete next[id];
        });
        return next;
      });
      queryClient.invalidateQueries({ queryKey: ["location-nodes"] });
      queryClient.invalidateQueries({ queryKey: ["items"] });
    }
  });

  const createCompartmentNode = useMutation({
    mutationFn: async () => {
      if (!selectedNode || selectedNode.node_type !== "FURNITURE" || !selectedFloorPlan) {
        throw new Error("가구를 먼저 선택하세요.");
      }

      const existingCompartments = floorLocations.filter(
        (node) => node.parent === selectedNode.id && node.node_type === "COMPARTMENT"
      );
      const createCount = existingCompartments.length === 0 ? 2 : 1;
      let knownNodes = floorLocations;
      const createdNodes: LocationNode[] = [];

      for (let index = 0; index < createCount; index += 1) {
        const sequence = existingCompartments.length + index + 1;
        const createdNode = await api.post<LocationNode>("/location-nodes/", {
          home: selectedFloorPlan.home,
          floor_plan: selectedFloorPlan.id,
          parent: selectedNode.id,
          node_type: "COMPARTMENT",
          code: nextLocationCode(knownNodes, selectedNode.id, "COMPARTMENT"),
          name: `${selectedNode.name}${sequence}층`,
          geometry_json: {},
          metadata_json: {}
        });
        knownNodes = [...knownNodes, createdNode];
        createdNodes.push(createdNode);
      }

      return createdNodes;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["location-nodes"] });
    }
  });

  useEffect(() => {
    function handleDeleteKey(event: KeyboardEvent) {
      if (event.key !== "Delete" || isTypingTarget(event.target) || deleteLocationNode.isPending) {
        return;
      }
      if (!selectedNode) {
        return;
      }
      event.preventDefault();
      confirmDeleteNode(selectedNode);
    }

    window.addEventListener("keydown", handleDeleteKey);
    return () => window.removeEventListener("keydown", handleDeleteKey);
  }, [deleteLocationNode.isPending, floorLocations, flatTree, selectedNode]);

  function createRectangle() {
    if (selectedFloorPlan) {
      createNode.mutate("ROOM");
    }
  }

  function renameSelectedFloorPlan() {
    if (!selectedFloorPlan || updateFloorPlan.isPending) {
      return;
    }

    const nextName = window.prompt("도면 이름을 입력하세요.", selectedFloorPlan.name)?.trim();
    if (!nextName || nextName === selectedFloorPlan.name) {
      return;
    }

    updateFloorPlan.mutate({
      id: selectedFloorPlan.id,
      payload: { name: nextName }
    });
  }

  function submitDetails(event: FormEvent) {
    event.preventDefault();
    if (!selectedNode || !selectedFloorPlan) {
      return;
    }

    if (!isDrawableType(selectedNode.node_type)) {
      updateNode.mutate({
        id: selectedNode.id,
        payload: {
          name: detailForm.name.trim()
        }
      });
      return;
    }

    const rect = makeRectFromDetailForm();
    const nodeType = detailForm.node_type;
    const parentId =
      nodeType === "FURNITURE" ? findContainingRoomId(rect, selectedNode.id) : null;
    const shouldRegenerateCode =
      parentId !== (selectedNode.parent ?? null) || nodeType !== selectedNode.node_type;
    const code = shouldRegenerateCode
      ? nextLocationCode(
          floorLocations.filter((node) => node.id !== selectedNode.id),
          parentId,
          nodeType
        )
      : selectedNode.code;

    setGeometryDrafts((current) => ({ ...current, [selectedNode.id]: rect }));
    maybeExpandFloorPlan(rect);
    updateNode.mutate({
      id: selectedNode.id,
      payload: {
        parent: parentId,
        node_type: nodeType,
        code,
        name: detailForm.name.trim(),
        geometry_json: rect
      }
    });
  }

  function deleteNode(node: LocationNode, nextSelectedId?: number | null) {
    if (deleteLocationNode.isPending) {
      return;
    }
    const deletedIds = getNodeAndDescendantIds(node.id);
    deleteLocationNode.mutate({
      id: node.id,
      deletedIds,
      nextSelectedId: nextSelectedId ?? getNextSelectedNodeId(node, deletedIds)
    });
  }

  function confirmDeleteNode(node: LocationNode, nextSelectedId?: number | null) {
    if (
      node.node_type === "COMPARTMENT" &&
      !window.confirm(`정말 "${node.name}" 칸을 삭제하시겠습니까?`)
    ) {
      return;
    }

    deleteNode(node, nextSelectedId);
  }

  function deleteSelectedNode() {
    if (selectedNode) {
      confirmDeleteNode(selectedNode);
    }
  }

  function getNodeAndDescendantIds(nodeId: number) {
    const ids = new Set<number>([nodeId]);
    let found = true;

    while (found) {
      found = false;
      floorLocations.forEach((node) => {
        if (node.parent && ids.has(node.parent) && !ids.has(node.id)) {
          ids.add(node.id);
          found = true;
        }
      });
    }

    return [...ids];
  }

  function getNextSelectedNodeId(node: LocationNode, deletedIds: number[]) {
    if (node.parent && !deletedIds.includes(node.parent)) {
      return node.parent;
    }

    return flatTree.find((item) => !deletedIds.includes(item.id))?.id ?? null;
  }

  function nextDefaultNodeName(nodeType: LocationNodeType) {
    const baseName = nodeType === "FURNITURE" ? "새 가구" : "새 방";
    const existingNames = new Set(floorLocations.map((node) => node.name));

    if (!existingNames.has(baseName)) {
      return baseName;
    }

    let number = 2;
    let name = `${baseName} ${number}`;
    while (existingNames.has(name)) {
      number += 1;
      name = `${baseName} ${number}`;
    }

    return name;
  }

  function updateSelectedType(nodeType: LocationNodeType) {
    if (!selectedNode) {
      return;
    }

    const rect = selectedRect ?? fallbackRect(0);
    const parentId =
      nodeType === "FURNITURE"
        ? findContainingRoomId(rect, selectedNode.id)
        : null;
    const code =
      parentId !== (selectedNode.parent ?? null) || nodeType !== selectedNode.node_type
        ? nextLocationCode(
            floorLocations.filter((node) => node.id !== selectedNode.id),
            parentId,
            nodeType
          )
        : selectedNode.code;

    setDetailForm((current) => ({
      ...current,
      node_type: nodeType
    }));
    updateNode.mutate({
      id: selectedNode.id,
      payload: {
        parent: parentId,
        node_type: nodeType,
        code
      }
    });
  }

  function makeRectFromDetailForm() {
    if (!selectedFloorPlan) {
      return fallbackRect(0);
    }
    return normalizeRect(
      constrainRect(
        {
          type: "rect",
          x: selectedRect?.x ?? 0,
          y: selectedRect?.y ?? 0,
          width: Number(detailForm.width),
          height: Number(detailForm.height),
          rotation: 0
        },
        detailForm.node_type
      )
    );
  }

  function maybeExpandFloorPlan(rect: RectGeometry) {
    if (!selectedFloorPlan) {
      return;
    }

    const nextSize = expandedSizeForRect(
      rect,
      selectedFloorPlan.width,
      selectedFloorPlan.height
    );
    if (nextSize.width === selectedFloorPlan.width && nextSize.height === selectedFloorPlan.height) {
      return;
    }

    updateFloorPlan.mutate({
      id: selectedFloorPlan.id,
      payload: nextSize
    });
  }

  function findContainingRoomId(rect: RectGeometry, excludeNodeId?: number) {
    const containingRoom = floorLocations.find((node, index) => {
      if (node.id === excludeNodeId || node.node_type !== "ROOM") {
        return false;
      }
      return rectContains(rectForNode(node, index, geometryDrafts), rect);
    });

    return containingRoom?.id ?? null;
  }

  function buildGeometryPayload(node: LocationNode, rect: RectGeometry) {
    if (node.node_type !== "FURNITURE") {
      return {
        geometry_json: rect
      };
    }

    const parentId = findContainingRoomId(rect, node.id);
    const shouldRegenerateCode = parentId !== (node.parent ?? null);
    return {
      parent: parentId,
      code: shouldRegenerateCode
        ? nextLocationCode(
            floorLocations.filter((location) => location.id !== node.id),
            parentId,
            node.node_type
          )
        : node.code,
      geometry_json: rect
    };
  }

  function pointFromEvent(event: PointerEvent<SVGSVGElement>, viewBox = viewportBox) {
    const svg = svgRef.current;
    if (!svg) {
      return { x: 0, y: 0 };
    }
    const box = svg.getBoundingClientRect();
    return {
      x: viewBox.x + ((event.clientX - box.left) / box.width) * viewBox.width,
      y: viewBox.y + ((event.clientY - box.top) / box.height) * viewBox.height
    };
  }

  function startPointer(event: PointerEvent<SVGElement>, node: LocationNode, rect: RectGeometry, mode: PointerMode) {
    event.preventDefault();
    event.stopPropagation();
    panRef.current = null;
    event.currentTarget.setPointerCapture(event.pointerId);
    setSelectedNodeId(node.id);
    const svgEvent = event as unknown as PointerEvent<SVGSVGElement>;
    const point = pointFromEvent(svgEvent);
    dragRef.current = {
      nodeId: node.id,
      mode,
      startX: point.x,
      startY: point.y,
      origin: rect,
      latest: rect,
      viewBox: viewportBox
    };
  }

  function updatePointer(event: PointerEvent<SVGSVGElement>) {
    const active = dragRef.current;
    if (!active) {
      updateCanvasPan(event);
      return;
    }
    if (!selectedFloorPlan) {
      return;
    }

    const point = pointFromEvent(event, active.viewBox);
    const dx = point.x - active.startX;
    const dy = point.y - active.startY;
    const next =
      active.mode === "move"
        ? { ...active.origin, x: active.origin.x + dx, y: active.origin.y + dy }
        : {
            ...active.origin,
            width: active.origin.width + dx,
            height: active.origin.height + dy
          };
    const activeNode = floorLocations.find((node) => node.id === active.nodeId);
    const snapTargets = floorLocations
      .filter(
        (node) =>
          node.id !== active.nodeId &&
          isDrawableType(node.node_type) &&
          node.node_type === activeNode?.node_type
      )
      .map((node) => {
        const index = floorLocations.findIndex((location) => location.id === node.id);
        return rectForNode(node, index, geometryDrafts);
      });
    const snapped = snapRect(next, snapTargets, selectedFloorPlan.width, selectedFloorPlan.height);
    const normalized = constrainRect(snapped, activeNode?.node_type ?? "ROOM");
    dragRef.current = { ...active, latest: normalized };
    setGeometryDrafts((current) => ({ ...current, [active.nodeId]: normalized }));
  }

  function handleCanvasWheel(event: WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    const direction = event.deltaY < 0 ? 1 : -1;
    setStageZoom((current) => {
      const next = current + direction * 0.12;
      return Math.min(3, Math.max(0.35, Number(next.toFixed(2))));
    });
  }

  function startCanvasPan(event: PointerEvent<SVGElement>) {
    if (dragRef.current) {
      return;
    }
    const target = event.target as SVGElement;
    if (target.closest(".shape") || target.closest(".resize-handle")) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    setSelectedNodeId(null);
    panRef.current = {
      startClientX: event.clientX,
      startClientY: event.clientY,
      originX: stagePan.x,
      originY: stagePan.y,
      viewBox: viewportBox
    };
  }

  function updateCanvasPan(event: PointerEvent<SVGSVGElement>) {
    const active = panRef.current;
    const svg = svgRef.current;
    if (!active || !svg) {
      return;
    }

    const box = svg.getBoundingClientRect();
    const dx = ((event.clientX - active.startClientX) / box.width) * active.viewBox.width;
    const dy = ((event.clientY - active.startClientY) / box.height) * active.viewBox.height;
    setStagePan({
      x: active.originX - dx,
      y: active.originY - dy
    });
  }

  function endPointer() {
    const active = dragRef.current;
    dragRef.current = null;
    if (panRef.current) {
      panRef.current = null;
    }
    if (!active) {
      return;
    }
    const node = floorLocations.find((location) => location.id === active.nodeId);
    if (!node) {
      return;
    }
    maybeExpandFloorPlan(active.latest);
    updateNode.mutate({
      id: active.nodeId,
      payload: buildGeometryPayload(node, active.latest)
    });
  }

  const selectedItems = selectedItemsQuery.data ?? [];

  function renderLocationTree(nodes: TreeNode[]) {
    return nodes.map((node) => {
      const hasChildren = node.children.length > 0;
      const Icon = hasChildren ? FolderOpen : Square;

      return (
        <div className="node-tree-branch" key={node.id}>
          <button
            className={`node-tree-item ${selectedNodeId === node.id ? "selected" : ""}`}
            type="button"
            onClick={() => setSelectedNodeId(node.id)}
            title={node.path}
          >
            <Icon aria-hidden="true" />
            <span>{node.name}</span>
            <strong>{node.full_code}</strong>
          </button>
          {hasChildren ? (
            <div className="node-tree-children">{renderLocationTree(node.children)}</div>
          ) : null}
        </div>
      );
    });
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <h1>도면 편집</h1>
        </div>
      </header>

      <section className="editor-toolbar panel">
        <label>
          집
          <select
            value={selectedHomeId}
            onChange={(event) => {
              const nextHomeId = event.target.value;
              const recentFloorPlanId = readRecentFloorPlanId();
              const nextFloorPlan = floorPlans.find(
                (floorPlan) =>
                  String(floorPlan.home) === nextHomeId &&
                  String(floorPlan.id) === recentFloorPlanId
              );
              const firstFloorPlan = floorPlans.find(
                (floorPlan) => String(floorPlan.home) === nextHomeId
              );

              setSelectedHomeId(nextHomeId);
              setSelectedFloorPlanId(nextFloorPlan ? String(nextFloorPlan.id) : firstFloorPlan ? String(firstFloorPlan.id) : "");
              setSelectedNodeId(null);
            }}
          >
            <option value="">선택</option>
            {homes.map((home) => (
              <option key={home.id} value={home.id}>
                {home.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          도면
          <select
            value={selectedFloorPlanId}
            onChange={(event) => {
              const nextFloorPlanId = event.target.value;
              setSelectedFloorPlanId(nextFloorPlanId);
              if (nextFloorPlanId) {
                saveRecentFloorPlanId(nextFloorPlanId);
              }
              setSelectedNodeId(null);
            }}
          >
            <option value="">선택</option>
            {visibleFloorPlans.map((floorPlan) => (
              <option key={floorPlan.id} value={floorPlan.id}>
                {floorPlan.name}
              </option>
            ))}
          </select>
        </label>
        <IconButton
          icon={Square}
          label="사각형 추가"
          disabled={!selectedFloorPlan || createNode.isPending}
          onClick={createRectangle}
        />
        <IconButton
          icon={Pencil}
          label="도면 이름 변경"
          variant="secondary"
          disabled={!selectedFloorPlan || updateFloorPlan.isPending}
          onClick={renameSelectedFloorPlan}
        />
      </section>
      <ErrorBanner error={createNode.error || updateFloorPlan.error} />

      <div className="grid editor-layout">
        <section className="panel editor-tree-panel">
          <div className="panel-header">
            <h2>
              <FolderOpen aria-hidden="true" />
              사각형 목록
            </h2>
          </div>
          {tree.length === 0 ? (
            <EmptyState title="등록된 사각형이 없습니다." />
          ) : (
            <div className="node-tree">{renderLocationTree(tree)}</div>
          )}
        </section>

        <section className="panel editor-stage-panel">
          <div className="panel-header">
            <h2>
              <Move aria-hidden="true" />
              배치
            </h2>
          </div>
          <ErrorBanner error={locationsQuery.error || updateNode.error} />
          {!selectedFloorPlan ? (
            <EmptyState title="선택된 도면이 없습니다." />
          ) : (
            <div className="floor-canvas" onWheel={handleCanvasWheel}>
              <svg
                ref={svgRef}
                className="drawing-surface"
                viewBox={`${viewportBox.x} ${viewportBox.y} ${viewportBox.width} ${viewportBox.height}`}
                role="img"
                aria-label={selectedFloorPlan.name}
                onPointerMove={updatePointer}
                onPointerUp={endPointer}
                onPointerLeave={endPointer}
                onPointerDown={(event) => {
                  if (event.target === event.currentTarget) {
                    startCanvasPan(event);
                  }
                }}
              >
                <rect
                  x={viewportBox.x}
                  y={viewportBox.y}
                  width={viewportBox.width}
                  height={viewportBox.height}
                  className="canvas-background"
                  onPointerDown={startCanvasPan}
                />
                {sortedDrawableLocations.map((node) => {
                  const index = floorLocations.findIndex((location) => location.id === node.id);
                  const rect = rectForNode(node, index >= 0 ? index : 0, geometryDrafts);
                  const colors = palette[node.node_type];
                  const selected = node.id === selectedNodeId;
                  return (
                    <g
                      key={node.id}
                      className={selected ? "shape selected" : "shape"}
                      onPointerDown={(event) => startPointer(event, node, rect, "move")}
                    >
                      <rect
                        x={rect.x}
                        y={rect.y}
                        width={rect.width}
                        height={rect.height}
                        rx="6"
                        fill={colors.fill}
                        stroke={colors.stroke}
                        strokeWidth={selected ? 4 : 2}
                        onPointerDown={(event) => startPointer(event, node, rect, "move")}
                      />
                      <text
                        x={rect.x + 10}
                        y={rect.y + 24}
                        fill="#17202a"
                        fontSize="16"
                        fontWeight="700"
                        pointerEvents="none"
                      >
                        {node.name}
                      </text>
                      <text
                        x={rect.x + 10}
                        y={rect.y + 46}
                        fill={colors.stroke}
                        fontSize="13"
                        fontWeight="700"
                        pointerEvents="none"
                      >
                        {node.full_code}
                      </text>
                      {selected ? (
                        <rect
                          className="resize-handle"
                          x={rect.x + rect.width - 12}
                          y={rect.y + rect.height - 12}
                          width="18"
                          height="18"
                          rx="4"
                          onPointerDown={(event) => startPointer(event, node, rect, "resize")}
                        />
                      ) : null}
                    </g>
                  );
                })}
              </svg>
            </div>
          )}
        </section>

        <section className="panel editor-detail-panel">
          <div className="panel-header">
            <h2>
              <Maximize2 aria-hidden="true" />
              선택 위치
            </h2>
          </div>
          {selectedNode ? (
            <>
              <ErrorBanner
                error={
                  updateNode.error ||
                  deleteLocationNode.error ||
                  createCompartmentNode.error ||
                  selectedItemsQuery.error
                }
              />
              <form className="form-grid" onSubmit={submitDetails}>
                <label>
                  이름
                  <input
                    value={detailForm.name}
                    onChange={(event) => setDetailForm({ ...detailForm, name: event.target.value })}
                    required
                  />
                </label>
                {isDrawableType(selectedNode.node_type) ? (
                  <label>
                    타입
                    <select
                      value={detailForm.node_type}
                      onChange={(event) => updateSelectedType(event.target.value as LocationNodeType)}
                    >
                      {editableTypes.map((nodeType) => (
                        <option key={nodeType} value={nodeType}>
                          {nodeTypeLabels[nodeType]}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <div className="readonly-field">
                    <span>타입</span>
                    <strong>{nodeTypeLabels[selectedNode.node_type] ?? selectedNode.node_type}</strong>
                  </div>
                )}
                {isDrawableType(selectedNode.node_type) ? (
                  <div className="inline-fields">
                    <label>
                      너비
                      <input
                        type="number"
                        min={rectLimits[detailForm.node_type as "ROOM" | "FURNITURE"].minWidth}
                        max={rectLimits[detailForm.node_type as "ROOM" | "FURNITURE"].maxWidth}
                        value={detailForm.width}
                        onChange={(event) => setDetailForm({ ...detailForm, width: event.target.value })}
                      />
                    </label>
                    <label>
                      높이
                      <input
                        type="number"
                        min={rectLimits[detailForm.node_type as "ROOM" | "FURNITURE"].minHeight}
                        max={rectLimits[detailForm.node_type as "ROOM" | "FURNITURE"].maxHeight}
                        value={detailForm.height}
                        onChange={(event) => setDetailForm({ ...detailForm, height: event.target.value })}
                      />
                    </label>
                  </div>
                ) : null}
                <IconButton icon={Save} label="저장" disabled={updateNode.isPending} type="submit" />
              </form>

              {selectedNode.node_type === "FURNITURE" ? (
                <div className="linked-items">
                  <div className="panel-header compact">
                    <h2>
                      <Layers aria-hidden="true" />
                      칸
                    </h2>
                    <IconButton
                      icon={Plus}
                      label="칸 추가"
                      variant="secondary"
                      disabled={createCompartmentNode.isPending}
                      onClick={() => createCompartmentNode.mutate()}
                    />
                  </div>
                  {selectedCompartments.length === 0 ? (
                    <EmptyState title="등록된 칸이 없습니다." />
                  ) : (
                    <div className="compartment-list">
                      {selectedCompartments.map((node) => (
                        <article key={node.id} className="compartment-row">
                          <button
                            className="compartment-main"
                            type="button"
                            onClick={() => setSelectedNodeId(node.id)}
                          >
                            <span>{node.name}</span>
                            <strong>{node.full_code}</strong>
                          </button>
                          <button
                            className="icon-only danger"
                            type="button"
                            title={`${node.name} 삭제`}
                            aria-label={`${node.name} 삭제`}
                            disabled={deleteLocationNode.isPending}
                            onClick={() => confirmDeleteNode(node, selectedNode.id)}
                          >
                            <Trash2 aria-hidden="true" />
                          </button>
                        </article>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}

              <div className="linked-items">
                <div className="panel-header compact">
                  <h2>물건</h2>
                  <span className="count-pill">{selectedItems.length}</span>
                </div>
                {selectedItems.length === 0 ? (
                  <EmptyState title="연결된 물건이 없습니다." />
                ) : (
                  <div className="selected-items-scroll">
                    {selectedItems.map((item) => (
                      <article key={item.id} className="row-card">
                        <div>
                          <strong>{item.name}</strong>
                          <span>{item.location_code || selectedNode.full_code}</span>
                        </div>
                        <span className="count-pill">{item.quantity}</span>
                      </article>
                    ))}
                  </div>
                )}
              </div>
              <IconButton
                icon={Trash2}
                label="선택 위치 삭제"
                variant="danger"
                className="editor-delete-location-button"
                disabled={deleteLocationNode.isPending}
                onClick={deleteSelectedNode}
              />
            </>
          ) : (
            <EmptyState title="선택된 위치가 없습니다." />
          )}
        </section>
      </div>
    </section>
  );
}
