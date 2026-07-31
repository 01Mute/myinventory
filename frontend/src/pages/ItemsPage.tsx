import { FormEvent, KeyboardEvent, MouseEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImagePlus, Plus, Search, Trash2, X } from "lucide-react";

import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { IconButton } from "../components/IconButton";
import { LocationPicker } from "../components/LocationPicker";
import type {
  Category,
  Item,
  ItemLocationHistory,
  LocationNode,
  Tag
} from "../types/api";
import { buildLocationTree } from "../utils/tree";
import { toggleSetValue } from "../utils/sets";

const NEW_CATEGORY_VALUE = "__new_category__";
const ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"];

type PanelMode = "create" | "edit" | null;

type ItemFormState = {
  name: string;
  category: string;
  newCategoryName: string;
  description: string;
  quantity: string;
  current_location_node: string;
  purchase_date: string;
  tagText: string;
};

const emptyItemForm: ItemFormState = {
  name: "",
  category: "",
  newCategoryName: "",
  description: "",
  quantity: "1",
  current_location_node: "",
  purchase_date: "",
  tagText: ""
};

function createItemFormDefaults(): ItemFormState {
  return {
    ...emptyItemForm,
    purchase_date: getTodayDateInputValue()
  };
}

export function ItemsPage() {
  const queryClient = useQueryClient();
  const editorPanelRef = useRef<HTMLElement | null>(null);
  const [filters, setFilters] = useState({
    q: "",
    category: "",
    tag: "",
    location_node_id: ""
  });
  const [panelMode, setPanelMode] = useState<PanelMode>(null);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [itemForm, setItemForm] = useState<ItemFormState>(emptyItemForm);
  const [initialItemForm, setInitialItemForm] = useState<ItemFormState>(emptyItemForm);
  const [expandedSearchLocationIds, setExpandedSearchLocationIds] = useState<Set<number>>(
    () => new Set()
  );
  const [expandedFormLocationIds, setExpandedFormLocationIds] = useState<Set<number>>(
    () => new Set()
  );
  const [debouncedSearchText, setDebouncedSearchText] = useState("");
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);

  const searchParams = useMemo(() => {
    const params = new URLSearchParams();
    if (filters.q.trim()) {
      params.set("q", filters.q.trim());
    }
    if (filters.category) {
      params.set("category", filters.category);
    }
    if (filters.tag.trim()) {
      params.set("tag", normalizeTagName(filters.tag));
    }
    if (filters.location_node_id) {
      params.set("location_node_id", filters.location_node_id);
      params.set("include_children", "true");
    }
    return params.toString();
  }, [filters]);

  const touchSearchParams = useMemo(() => {
    const q = debouncedSearchText.trim();
    if (!q) {
      return "";
    }

    const params = new URLSearchParams();
    params.set("q", q);
    if (filters.category) {
      params.set("category", filters.category);
    }
    if (filters.tag.trim()) {
      params.set("tag", normalizeTagName(filters.tag));
    }
    if (filters.location_node_id) {
      params.set("location_node_id", filters.location_node_id);
      params.set("include_children", "true");
    }
    return params.toString();
  }, [debouncedSearchText, filters.category, filters.location_node_id, filters.tag]);

  const itemsQuery = useQuery({
    queryKey: ["items", "list", searchParams],
    queryFn: () => api.getAll<Item>(`/items/${searchParams ? `?${searchParams}` : ""}`)
  });
  // The duplicate-name check and the selected-item lookup need the unfiltered
  // list. Keying it as the empty-filter list means that when no filter is
  // active this is literally the same query, instead of a second identical
  // request on every mount.
  const allItemsQuery = useQuery({
    queryKey: ["items", "list", ""],
    queryFn: () => api.getAll<Item>("/items/")
  });
  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.getAll<Category>("/categories/")
  });
  const tagsQuery = useQuery({ queryKey: ["tags"], queryFn: () => api.getAll<Tag>("/tags/") });
  const locationsQuery = useQuery({
    queryKey: ["location-nodes"],
    queryFn: () => api.getAll<LocationNode>("/location-nodes/")
  });

  const items = itemsQuery.data ?? [];
  const allItems = allItemsQuery.data ?? items;
  const categories = categoriesQuery.data ?? [];
  const tags = tagsQuery.data ?? [];
  const locations = locationsQuery.data ?? [];
  const locationTree = useMemo(() => buildLocationTree(locations), [locations]);
  const selectedItem = useMemo(
    () =>
      selectedItemId
        ? allItems.find((item) => item.id === selectedItemId) ??
          items.find((item) => item.id === selectedItemId) ??
          null
        : null,
    [allItems, items, selectedItemId]
  );
  const displayedPhotoUrl = photoPreviewUrl ?? selectedItem?.photo ?? null;
  const hasUnsavedChanges =
    panelMode !== null &&
    (JSON.stringify(itemForm) !== JSON.stringify(initialItemForm) || Boolean(photoFile));

  const historyQuery = useQuery({
    queryKey: ["item-history", selectedItemId],
    queryFn: () => api.getAll<ItemLocationHistory>(`/items/${selectedItemId ?? 0}/history/`),
    enabled: panelMode === "edit" && Boolean(selectedItemId)
  });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearchText(filters.q.trim());
    }, 1000);

    return () => window.clearTimeout(timer);
  }, [filters.q]);

  useEffect(() => {
    if (!photoFile) {
      setPhotoPreviewUrl(null);
      return;
    }

    const objectUrl = URL.createObjectURL(photoFile);
    setPhotoPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [photoFile]);

  useEffect(() => {
    if (!touchSearchParams || debouncedSearchText !== filters.q.trim()) {
      return;
    }

    let cancelled = false;
    api
      .post<Item[]>(`/items/touch-searched/?${touchSearchParams}`)
      .then((touchedItems) => {
        if (!cancelled && debouncedSearchText === filters.q.trim()) {
          queryClient.setQueriesData<Item[]>({ queryKey: ["items"] }, (current) =>
            mergeItems(current, touchedItems)
          );
        }
      })
      .catch(() => undefined);

    return () => {
      cancelled = true;
    };
  }, [debouncedSearchText, filters.q, queryClient, searchParams, touchSearchParams]);

  useEffect(() => {
    if (panelMode !== "edit" || !selectedItemId) {
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      api
        .post<Item>(`/items/${selectedItemId}/touch-last-checked/`)
        .then((touchedItem) => {
          if (cancelled) {
            return;
          }
          queryClient.setQueriesData<Item[]>({ queryKey: ["items"] }, (current) =>
            mergeItems(current, [touchedItem])
          );
        })
        .catch(() => undefined);
    }, 1000);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [panelMode, queryClient, selectedItemId]);

  const saveItem = useMutation({
    mutationFn: async () => {
      const categoryId = await resolveCategoryId();
      const tagIds = await resolveTagIds();
      const payload = {
        name: itemForm.name.trim(),
        category: categoryId,
        description: itemForm.description,
        quantity: Number(itemForm.quantity),
        current_location_node: itemForm.current_location_node
          ? Number(itemForm.current_location_node)
          : null,
        purchase_date: itemForm.purchase_date || null,
        tag_ids: tagIds
      };

      let savedItem: Item;
      if (panelMode === "edit" && selectedItemId) {
        savedItem = await api.patch<Item>(`/items/${selectedItemId}/`, payload);
      } else {
        savedItem = await api.post<Item>("/items/", payload);
      }

      if (photoFile) {
        const formData = new FormData();
        formData.append("photo", photoFile);
        savedItem = await api.post<Item>(`/items/${savedItem.id}/photo/`, formData);
      }

      return savedItem;
    },
    onSuccess: (savedItem) => {
      queryClient.setQueryData<Item[]>(["items", "list", searchParams], (current) =>
        upsertItem(current, savedItem)
      );
      queryClient.setQueryData<Item[]>(["items", "list", ""], (current) =>
        upsertItem(current, savedItem)
      );
      queryClient.invalidateQueries({ queryKey: ["items"] });
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      queryClient.invalidateQueries({ queryKey: ["item-history", savedItem.id] });
      setPhotoFile(null);

      if (panelMode === "edit") {
        setSelectedItemId(savedItem.id);
        const nextForm = formFromItem(savedItem);
        setItemForm(nextForm);
        setInitialItemForm(nextForm);
        return;
      }

      setFilters({
        q: "",
        category: "",
        tag: "",
        location_node_id: ""
      });
      setSelectedItemId(null);
      setItemForm(emptyItemForm);
      setInitialItemForm(emptyItemForm);
      setPanelMode(null);
    }
  });

  const deleteItem = useMutation({
    mutationFn: (item: Item) => api.delete<null>(`/items/${item.id}/`),
    onSuccess: (_data, item) => {
      queryClient.setQueriesData<Item[]>({ queryKey: ["items"] }, (current) =>
        removeItem(current, item.id)
      );
      queryClient.invalidateQueries({ queryKey: ["item-history", item.id] });
      if (selectedItemId === item.id) {
        closePanel();
      }
    }
  });

  async function resolveCategoryId() {
    if (itemForm.category !== NEW_CATEGORY_VALUE) {
      return itemForm.category ? Number(itemForm.category) : null;
    }

    const name = itemForm.newCategoryName.trim();
    if (!name) {
      throw new Error("새 카테고리 이름을 입력하세요.");
    }

    const existingCategory = categories.find(
      (category) => category.name.toLowerCase() === name.toLowerCase()
    );
    if (existingCategory) {
      return existingCategory.id;
    }

    const category = await api.post<Category>("/categories/", { name });
    return category.id;
  }

  async function resolveTagIds() {
    const names = parseTagNames(itemForm.tagText);
    const ids: number[] = [];
    let knownTags = tags;

    for (const name of names) {
      const existingTag = knownTags.find((tag) => tag.name.toLowerCase() === name.toLowerCase());
      if (existingTag) {
        ids.push(existingTag.id);
        continue;
      }

      const tag = await api.post<Tag>("/tags/", { name });
      knownTags = [...knownTags, tag];
      ids.push(tag.id);
    }

    return ids;
  }

  function submitItem(event: FormEvent) {
    event.preventDefault();
    if (panelMode === "create" && !confirmDuplicateItem()) {
      return;
    }
    saveItem.mutate();
  }

  function confirmDuplicateItem() {
    const name = itemForm.name.trim().toLowerCase();
    const duplicates = allItems.filter((item) => item.name.trim().toLowerCase() === name);
    if (duplicates.length === 0) {
      return true;
    }

    return window.confirm(
      [
        "동일한 물건이 존재합니다. 등록하시겠습니까?",
        "",
        ...duplicates.slice(0, 5).map(
          (item) =>
            `- ${item.name} / ${item.location_path || "미지정"} / 수량 ${item.quantity} / ${
              item.category_name || "카테고리 없음"
            }`
        )
      ].join("\n")
    );
  }

  function openCreatePanel() {
    if (
      hasUnsavedChanges &&
      !window.confirm("수정사항이 있습니다. 저장하지 않고 새 물건을 등록하시겠습니까?")
    ) {
      return;
    }
    const nextForm = createItemFormDefaults();
    setPanelMode("create");
    setSelectedItemId(null);
    setItemForm(nextForm);
    setInitialItemForm(nextForm);
    setPhotoFile(null);
  }

  function openEditPanel(item: Item) {
    if (hasUnsavedChanges && !window.confirm("수정사항이 있습니다. 저장하지 않고 다른 물건을 여시겠습니까?")) {
      return;
    }
    const nextForm = formFromItem(item);
    setPanelMode("edit");
    setSelectedItemId(item.id);
    setItemForm(nextForm);
    setInitialItemForm(nextForm);
    setPhotoFile(null);
    if (item.current_location_node) {
      const locationId = item.current_location_node;
      setExpandedFormLocationIds((current) =>
        addAncestorIds(current, locationId, locations)
      );
    }
  }

  function closePanel() {
    setPanelMode(null);
    setSelectedItemId(null);
    setItemForm(emptyItemForm);
    setInitialItemForm(emptyItemForm);
    setPhotoFile(null);
  }

  /**
   * Closing with unsaved edits offers three outcomes, not two.
   *
   * This previously asked "저장하시겠습니까?" and treated Cancel as "throw the
   * edits away", with no way to stay in the panel. Since any stray mousedown
   * outside the panel routes here, one misclick plus a reflex Cancel destroyed
   * the work. Now Cancel keeps the panel open and discarding is explicit.
   */
  async function requestClosePanel() {
    if (!panelMode || saveItem.isPending) {
      return;
    }
    if (!hasUnsavedChanges) {
      closePanel();
      return;
    }

    if (!window.confirm("수정사항이 있습니다. 저장하고 닫으시겠습니까?\n\n취소를 누르면 계속 편집합니다.")) {
      if (window.confirm("편집한 내용을 저장하지 않고 버리시겠습니까?")) {
        closePanel();
      }
      return;
    }

    if (panelMode === "create" && !confirmDuplicateItem()) {
      return;
    }

    try {
      await saveItem.mutateAsync();
      closePanel();
    } catch {
      return;
    }
  }

  function confirmDeleteItem(item: Item) {
    if (window.confirm(`정말 "${item.name}" 물건을 삭제하시겠습니까?`)) {
      deleteItem.mutate(item);
    }
  }

  function handlePageMouseDown(event: MouseEvent<HTMLElement>) {
    if (!panelMode || saveItem.isPending) {
      return;
    }

    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (editorPanelRef.current?.contains(target) || isPanelSafeTarget(target)) {
      return;
    }

    void requestClosePanel();
  }

  function handleItemRowKeyDown(event: KeyboardEvent<HTMLTableRowElement>, item: Item) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openEditPanel(item);
    }
  }

  function handlePhotoChange(file: File | undefined) {
    if (!file) {
      setPhotoFile(null);
      return;
    }

    if (!isAllowedImageFile(file)) {
      window.alert("사진 파일은 JPG, PNG, GIF, WEBP 형식만 업로드할 수 있습니다.");
      setPhotoFile(null);
      return;
    }

    setPhotoFile(file);
  }

  return (
    <section className="page-stack" onMouseDown={handlePageMouseDown}>
      <header className="page-header">
        <div>
          <h1>물건 검색</h1>
        </div>
      </header>

      <section className="panel">
        <div className="panel-header">
          <h2>
            <Search aria-hidden="true" />
            검색
          </h2>
          <div className="row-actions">
            <span className="count-pill">총 {items.length}건</span>
            <IconButton
              icon={Plus}
              label="물건 추가"
              disabled={panelMode === "create"}
              onClick={openCreatePanel}
            />
          </div>
        </div>
        <div className="filters">
          <label>
            검색어
            <input
              value={filters.q}
              onChange={(event) => setFilters({ ...filters, q: event.target.value })}
              placeholder="물건명, 설명, 위치 코드"
            />
          </label>
          <label>
            카테고리
            <select
              value={filters.category}
              onChange={(event) => setFilters({ ...filters, category: event.target.value })}
            >
              <option value="">전체</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            태그
            <input
              list="tag-search-options"
              value={filters.tag}
              onChange={(event) => setFilters({ ...filters, tag: event.target.value })}
              placeholder="#태그"
            />
            <datalist id="tag-search-options">
              {tags.map((tag) => (
                <option key={tag.id} value={`#${tag.name}`} />
              ))}
            </datalist>
          </label>
          <div className="field-block">
            <span className="field-label">위치</span>
            <LocationPicker
              emptyLabel="전체"
              expandedIds={expandedSearchLocationIds}
              selectedId={filters.location_node_id}
              tree={locationTree}
              onSelect={(locationId) =>
                setFilters({
                  ...filters,
                  location_node_id: locationId
                })
              }
              onToggle={(nodeId) =>
                setExpandedSearchLocationIds((current) => toggleSetValue(current, nodeId))
              }
            />
          </div>
        </div>
      </section>

      <div className={`inventory-workspace ${panelMode ? "with-editor" : ""}`}>
        <section className="panel">
          <div className="panel-header">
            <h2>목록</h2>
          </div>
          <ErrorBanner
            error={
              itemsQuery.error ||
              categoriesQuery.error ||
              tagsQuery.error ||
              locationsQuery.error ||
              deleteItem.error
            }
          />
          {items.length === 0 ? (
            <EmptyState title="표시할 물건이 없습니다." />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>물건</th>
                    <th>위치</th>
                    <th>수량</th>
                    <th>마지막 검색일자</th>
                    <th aria-label="삭제" />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.id}
                      className={`item-row ${selectedItemId === item.id ? "selected" : ""}`}
                      role="button"
                      tabIndex={0}
                      onClick={() => openEditPanel(item)}
                      onKeyDown={(event) => handleItemRowKeyDown(event, item)}
                    >
                      <td>
                        <strong>{item.name}</strong>
                        <span>{item.category_name || "카테고리 없음"}</span>
                      </td>
                      <td>
                        <strong>{item.location_code || "-"}</strong>
                        <span>{item.location_path || "미지정"}</span>
                      </td>
                      <td>{item.quantity}</td>
                      <td>{formatDateTime(item.last_checked_at)}</td>
                      <td className="table-action-cell">
                        <button
                          className="icon-only danger"
                          type="button"
                          title={`${item.name} 삭제`}
                          aria-label={`${item.name} 삭제`}
                          disabled={deleteItem.isPending}
                          onClick={(event) => {
                            event.stopPropagation();
                            confirmDeleteItem(item);
                          }}
                        >
                          <Trash2 aria-hidden="true" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {panelMode ? (
          <section className="panel item-editor-panel" ref={editorPanelRef}>
            <div className="panel-header">
              <h2>{panelMode === "edit" ? "수정" : "등록"}</h2>
              <button
                className="icon-only"
                type="button"
                title="닫기"
                onClick={() => void requestClosePanel()}
              >
                <X aria-hidden="true" />
              </button>
            </div>
            <ErrorBanner error={saveItem.error || historyQuery.error || deleteItem.error} />

            <form className="form-grid" onSubmit={submitItem}>
              <label>
                이름
                <input
                  value={itemForm.name}
                  onChange={(event) => setItemForm({ ...itemForm, name: event.target.value })}
                  required
                />
              </label>
              <label>
                카테고리
                <select
                  value={itemForm.category}
                  onChange={(event) =>
                    setItemForm({
                      ...itemForm,
                      category: event.target.value,
                      newCategoryName:
                        event.target.value === NEW_CATEGORY_VALUE ? itemForm.newCategoryName : ""
                    })
                  }
                >
                  <option value="">없음</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                  <option value={NEW_CATEGORY_VALUE}>새 카테고리 추가</option>
                </select>
              </label>
              {itemForm.category === NEW_CATEGORY_VALUE ? (
                <label>
                  새 카테고리 이름
                  <input
                    value={itemForm.newCategoryName}
                    onChange={(event) =>
                      setItemForm({ ...itemForm, newCategoryName: event.target.value })
                    }
                    required
                  />
                </label>
              ) : null}
              <div className="field-block">
                <span className="field-label">위치</span>
                <LocationPicker
                  emptyLabel="미지정"
                  expandedIds={expandedFormLocationIds}
                  selectedId={itemForm.current_location_node}
                  tree={locationTree}
                  onSelect={(locationId) =>
                    setItemForm({ ...itemForm, current_location_node: locationId })
                  }
                  onToggle={(nodeId) =>
                    setExpandedFormLocationIds((current) => toggleSetValue(current, nodeId))
                  }
                />
              </div>
              <div className="photo-field">
                <span className="field-label">사진</span>
                {displayedPhotoUrl ? (
                  <img className="item-photo-preview" src={displayedPhotoUrl} alt={itemForm.name} />
                ) : (
                  <div className="item-photo-placeholder">사진 없음</div>
                )}
                <label className="file-picker">
                  <ImagePlus aria-hidden="true" />
                  <span>사진 선택</span>
                  <input
                    accept=".jpg,.jpeg,.png,.gif,.webp"
                    type="file"
                    onChange={(event) => handlePhotoChange(event.target.files?.[0])}
                  />
                </label>
                {photoFile ? <span className="file-name">{photoFile.name}</span> : null}
              </div>
              <div className="inline-fields">
                <label>
                  수량
                  <input
                    type="number"
                    min="1"
                    value={itemForm.quantity}
                    onChange={(event) => setItemForm({ ...itemForm, quantity: event.target.value })}
                    required
                  />
                </label>
                <label>
                  보관일자
                  <input
                    type="date"
                    value={itemForm.purchase_date}
                    onChange={(event) =>
                      setItemForm({ ...itemForm, purchase_date: event.target.value })
                    }
                  />
                </label>
              </div>
              <label>
                태그
                <input
                  value={itemForm.tagText}
                  onChange={(event) => setItemForm({ ...itemForm, tagText: event.target.value })}
                  placeholder="#태그"
                />
              </label>
              <label>
                설명
                <textarea
                  value={itemForm.description}
                  onChange={(event) =>
                    setItemForm({ ...itemForm, description: event.target.value })
                  }
                  rows={3}
                />
              </label>
              <IconButton
                icon={Plus}
                label={panelMode === "edit" ? "물건 수정" : "물건 추가"}
                disabled={saveItem.isPending}
                type="submit"
              />
            </form>

            {panelMode === "edit" && selectedItem ? (
              <div className="item-detail-sections">
                <section className="detail-section">
                  <div className="section-heading">
                    <h3>이동 이력</h3>
                    <span>{selectedItem.location_path || "미지정"}</span>
                  </div>
                  {historyQuery.isLoading ? (
                    <EmptyState title="이동 이력을 불러오는 중입니다." />
                  ) : (historyQuery.data ?? []).length === 0 ? (
                    <EmptyState title="아직 이동 이력이 없습니다." />
                  ) : (
                    <ul className="history-list">
                      {(historyQuery.data ?? []).map((history) => (
                        <li key={history.id}>
                          <span>{formatDateTime(history.moved_at)}</span>
                          <strong>
                            {history.from_location_path || "미지정"} →{" "}
                            {history.to_location_path || "미지정"}
                          </strong>
                          {history.memo ? <em>{history.memo}</em> : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </div>
            ) : null}
            {panelMode === "edit" && selectedItem ? (
              <IconButton
                icon={Trash2}
                label="물건 삭제"
                variant="danger"
                disabled={deleteItem.isPending}
                onClick={() => confirmDeleteItem(selectedItem)}
              />
            ) : null}
          </section>
        ) : null}
      </div>
    </section>
  );
}

function normalizeTagName(value: string) {
  return value.trim().replace(/^#+/, "");
}

function parseTagNames(value: string) {
  const seen = new Set<string>();
  return value
    .split(/[\s,]+/)
    .map(normalizeTagName)
    .filter(Boolean)
    .filter((name) => {
      const key = name.toLowerCase();
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).format(new Date(value));
}

function getTodayDateInputValue() {
  const now = new Date();
  const offsetDate = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return offsetDate.toISOString().slice(0, 10);
}

function formFromItem(item: Item): ItemFormState {
  return {
    name: item.name,
    category: item.category ? String(item.category) : "",
    newCategoryName: "",
    description: item.description,
    quantity: String(item.quantity),
    current_location_node: item.current_location_node ? String(item.current_location_node) : "",
    purchase_date: item.purchase_date ?? "",
    tagText: item.tags.map((tag) => `#${tag.name}`).join(" ")
  };
}

function upsertItem(items: Item[] | undefined, savedItem: Item) {
  if (!items) {
    return [savedItem];
  }

  const exists = items.some((item) => item.id === savedItem.id);
  const next = exists
    ? items.map((item) => (item.id === savedItem.id ? savedItem : item))
    : [savedItem, ...items];

  return [...next].sort((a, b) => a.name.localeCompare(b.name) || a.id - b.id);
}

function mergeItems(items: Item[] | undefined, updatedItems: Item[]) {
  if (!items) {
    return items;
  }

  const updatedById = new Map(updatedItems.map((item) => [item.id, item]));
  return items.map((item) => updatedById.get(item.id) ?? item);
}

function removeItem(items: Item[] | undefined, itemId: number) {
  return items?.filter((item) => item.id !== itemId);
}

function isAllowedImageFile(file: File) {
  const fileName = file.name.toLowerCase();
  const hasAllowedExtension = ALLOWED_IMAGE_EXTENSIONS.some((extension) =>
    fileName.endsWith(extension)
  );
  return hasAllowedExtension && file.type.startsWith("image/");
}

function isPanelSafeTarget(target: HTMLElement) {
  return Boolean(
    target.closest(
      [
        "button",
        "input",
        "select",
        "textarea",
        "a",
        "label",
        ".item-row",
        ".location-dropdown",
        ".location-picker"
      ].join(",")
    )
  );
}

function addAncestorIds(values: Set<number>, locationId: number, locations: LocationNode[]) {
  const next = new Set(values);
  const byId = new Map(locations.map((location) => [location.id, location]));
  let current = byId.get(locationId);

  while (current?.parent) {
    next.add(current.parent);
    current = byId.get(current.parent);
  }

  return next;
}
