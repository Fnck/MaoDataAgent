import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { BusinessActivity } from "../types";

interface FlowNode {
  id: number;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface FlowEdge {
  from: string;
  to: string;
}

interface Props {
  activities: BusinessActivity[];
  onEdit: (activity: BusinessActivity) => void;
  onDelete: (activity: BusinessActivity) => void;
  onAdd: () => void;
}

const NODE_W = 180;
const NODE_H = 56;
const LAYER_GAP_Y = 100;
const NODE_GAP_X = 30;
const PADDING = 40;

export default function ActivityFlowChart({
  activities,
  onEdit,
  onDelete,
  onAdd,
}: Props) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<number | null>(null);

  const { nodes, edges, svgWidth, svgHeight } = useMemo(() => {
    if (activities.length === 0) {
      return { nodes: [], edges: [], svgWidth: 400, svgHeight: 200 };
    }

    const nameMap = new Map<string, BusinessActivity>();
    activities.forEach((a) => nameMap.set(a.name, a));

    const successors = new Map<string, string[]>();
    const predecessors = new Map<string, string[]>();

    activities.forEach((a) => {
      const post =
        a.post_activities
          ?.split(",")
          .map((s) => s.trim())
          .filter(Boolean)
          .filter((name) => nameMap.has(name)) ?? [];
      successors.set(a.name, post);
      post.forEach((target) => {
        if (!predecessors.has(target)) predecessors.set(target, []);
        predecessors.get(target)!.push(a.name);
      });
    });

    const layers: string[][] = [];
    const visited = new Set<string>();
    const inDegree = new Map<string, number>();
    activities.forEach((a) => {
      const preds = predecessors.get(a.name) ?? [];
      inDegree.set(a.name, preds.length);
    });

    const queue: string[] = [];
    inDegree.forEach((deg, name) => {
      if (deg === 0) queue.push(name);
    });

    activities.forEach((a) => {
      if (inDegree.has(a.name)) return;
      inDegree.set(a.name, 0);
      queue.push(a.name);
    });

    while (queue.length > 0) {
      const currentLayer: string[] = [];
      const nextQueue: string[] = [];

      for (const name of queue) {
        if (visited.has(name)) continue;
        visited.add(name);
        currentLayer.push(name);

        const succs = successors.get(name) ?? [];
        for (const succ of succs) {
          const deg = (inDegree.get(succ) ?? 1) - 1;
          inDegree.set(succ, deg);
          if (deg === 0 && !visited.has(succ)) {
            nextQueue.push(succ);
          }
        }
      }

      if (currentLayer.length > 0) layers.push(currentLayer);
      queue.length = 0;
      queue.push(...nextQueue);
    }

    const unvisited = activities.filter((a) => !visited.has(a.name));
    if (unvisited.length > 0) {
      layers.push(unvisited.map((a) => a.name));
    }

    const edges: FlowEdge[] = [];
    activities.forEach((a) => {
      const post = successors.get(a.name) ?? [];
      post.forEach((target) => {
        edges.push({ from: a.name, to: target });
      });
    });

    const nodes: FlowNode[] = [];
    const maxNodesInLayer = Math.max(...layers.map((l) => l.length), 1);

    layers.forEach((layer, li) => {
      layer.forEach((name, ni) => {
        const act = nameMap.get(name)!;
        const layerWidth = layer.length * (NODE_W + NODE_GAP_X) - NODE_GAP_X;
        const totalWidth = Math.max(layerWidth, maxNodesInLayer * (NODE_W + NODE_GAP_X) - NODE_GAP_X);
        const startX = PADDING + (totalWidth - layerWidth) / 2;
        nodes.push({
          id: act.activity_id,
          name: act.name,
          x: startX + ni * (NODE_W + NODE_GAP_X),
          y: PADDING + li * (NODE_H + LAYER_GAP_Y),
          width: NODE_W,
          height: NODE_H,
        });
      });
    });

    const svgWidth = PADDING * 2 + maxNodesInLayer * (NODE_W + NODE_GAP_X) - NODE_GAP_X;
    const svgHeight = PADDING * 2 + layers.length * (NODE_H + LAYER_GAP_Y) - LAYER_GAP_Y;

    return { nodes, edges, svgWidth, svgHeight };
  }, [activities]);

  if (activities.length === 0) {
    return (
      <div className="text-center py-8 text-surface-400">
        <p>{t("ontology.noActivities")}</p>
        <button
          onClick={onAdd}
          className="btn-primary text-sm mt-3"
        >
          {t("ontology.addActivity")}
        </button>
      </div>
    );
  }

  const nodeByName = new Map(nodes.map((n) => [n.name, n]));

  return (
    <div className="relative">
      {/* Header with actions */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-semibold text-surface-700">{t("ontology.businessActivitiesFlow")}</h3>
        <button
          onClick={onAdd}
          className="btn-primary text-sm"
        >
          {t("ontology.addActivity")}
        </button>
      </div>

      {/* SVG Flow Chart */}
      <div className="bg-white border border-surface-200/60 rounded-2xl shadow-card overflow-auto" style={{ maxHeight: "calc(100vh - 280px)" }}>
        <svg
          width={svgWidth}
          height={svgHeight}
          className="block"
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="10"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#868e96" />
            </marker>
          </defs>

          {/* Edges */}
          {edges.map((edge, i) => {
            const fromNode = nodeByName.get(edge.from);
            const toNode = nodeByName.get(edge.to);
            if (!fromNode || !toNode) return null;

            const x1 = fromNode.x + fromNode.width / 2;
            const y1 = fromNode.y + fromNode.height;
            const x2 = toNode.x + toNode.width / 2;
            const y2 = toNode.y;

            return (
              <g key={`edge-${i}`}>
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2 - 10}
                  stroke="#868e96"
                  strokeWidth={1.5}
                  markerEnd="url(#arrowhead)"
                />
              </g>
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const isSelected = selected === node.id;
            return (
              <g
                key={node.id}
                className="cursor-pointer"
                onClick={() => setSelected(isSelected ? null : node.id)}
                onDoubleClick={() => {
                  const act = activities.find((a) => a.activity_id === node.id);
                  if (act) onEdit(act);
                }}
              >
                <rect
                  x={node.x}
                  y={node.y}
                  width={node.width}
                  height={node.height}
                  rx={12}
                  fill={isSelected ? "#f0f4ff" : "#f8f9fb"}
                  stroke={isSelected ? "#4c6ef5" : "#dee2e6"}
                  strokeWidth={isSelected ? 2 : 1}
                  className="transition-colors"
                />
                <text
                  x={node.x + node.width / 2}
                  y={node.y + node.height / 2}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="text-xs font-medium"
                  fill="#343a40"
                  style={{ fontSize: 12 }}
                >
                  {node.name}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Selected node detail panel */}
      {selected !== null && (() => {
        const act = activities.find((a) => a.activity_id === selected);
        if (!act) return null;
        return (
          <div className="mt-4 p-4 bg-brand-50/50 border border-brand-100 rounded-2xl animate-slide-up">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <p className="text-sm font-semibold text-brand-900">{act.name}</p>
                {act.description && (
                  <p className="text-sm text-surface-600 mt-1">{act.description}</p>
                )}
                <div className="flex gap-4 mt-2 text-xs text-surface-500">
                  {act.pre_activities && <span>{t("ontology.pre")}: {act.pre_activities}</span>}
                  {act.post_activities && <span>{t("ontology.post")}: {act.post_activities}</span>}
                </div>
                {act.input_entities && (
                  <p className="text-xs text-surface-400 mt-1">{t("ontology.input")}: {act.input_entities}</p>
                )}
                {act.output_entities && (
                  <p className="text-xs text-surface-400 mt-1">{t("ontology.output")}: {act.output_entities}</p>
                )}
                {act.operated_objects && (
                  <p className="text-xs text-surface-400 mt-1">{t("ontology.objects")}: {act.operated_objects}</p>
                )}
                {act.node_metrics && (
                  <p className="text-xs text-surface-400 mt-1">{t("ontology.nodeMetrics")}: {act.node_metrics}</p>
                )}
              </div>
              <div className="flex gap-2 shrink-0 ml-3">
                <button
                  onClick={() => onEdit(act)}
                  className="text-sm text-brand-500 font-medium hover:text-brand-700 transition-colors"
                >
                  {t("ontology.edit")}
                </button>
                <button
                  onClick={() => { onDelete(act); setSelected(null); }}
                  className="text-sm text-semantic-danger-500 font-medium hover:text-semantic-danger-700 transition-colors"
                >
                  {t("ontology.delete")}
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      <p className="text-xs text-surface-400 mt-3 text-center">
        {t("ontology.flowHint")}
      </p>
    </div>
  );
}
