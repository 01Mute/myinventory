export type User = {
  id: number;
  username: string;
  email: string;
  nickname: string;
  created_at: string;
  updated_at: string;
};

export type Home = {
  id: number;
  owner: number;
  name: string;
  address_optional: string;
  created_at: string;
  updated_at: string;
};

export type FloorPlan = {
  id: number;
  home: number;
  home_name: string;
  name: string;
  width: number;
  height: number;
  unit: "PX" | "CM" | "M";
  background_image: string | null;
  created_at: string;
  updated_at: string;
};

export type LocationNodeType =
  | "HOME"
  | "FLOOR"
  | "ROOM"
  | "ZONE"
  | "FURNITURE"
  | "COMPARTMENT"
  | "BOX"
  | "CUSTOM";

export type LocationNode = {
  id: number;
  home: number;
  home_name: string;
  floor_plan: number | null;
  floor_plan_name: string | null;
  parent: number | null;
  node_type: LocationNodeType;
  code: string;
  name: string;
  full_code: string;
  path: string;
  level: number;
  geometry_json: Record<string, unknown>;
  metadata_json: Record<string, unknown>;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type Category = {
  id: number;
  owner: number;
  name: string;
  created_at: string;
  updated_at: string;
};

export type Tag = {
  id: number;
  owner: number;
  name: string;
  created_at: string;
};

export type Item = {
  id: number;
  owner: number;
  name: string;
  category: number | null;
  category_name: string | null;
  description: string;
  quantity: number;
  current_location_node: number | null;
  location_code: string | null;
  location_path: string | null;
  photo: string | null;
  purchase_price: string | null;
  purchase_date: string | null;
  status: "ACTIVE" | "MISSING" | "ARCHIVED";
  last_checked_at: string | null;
  tags: Tag[];
  created_at: string;
  updated_at: string;
};

export type ItemLocationHistory = {
  id: number;
  item: number;
  from_location_node: number | null;
  from_location_code: string | null;
  from_location_path: string | null;
  to_location_node: number | null;
  to_location_code: string | null;
  to_location_path: string | null;
  memo: string;
  moved_at: string;
  created_by: number | null;
  created_at: string;
};

export type TreeNode = LocationNode & {
  children: TreeNode[];
};

export type RectGeometry = {
  type: "rect";
  x: number;
  y: number;
  width: number;
  height: number;
  rotation?: number;
};
