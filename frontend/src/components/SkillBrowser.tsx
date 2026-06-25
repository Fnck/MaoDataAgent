import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import * as api from "../api";

interface SkillInfo {
  name: string;
  display_name: string;
  description: string;
}

interface SkillGroup {
  name: string;
  skills: SkillInfo[];
}

export default function SkillBrowser() {
  const { t } = useTranslation();
  const token = useStore((s) => s.token)!;
  const [groups, setGroups] = useState<SkillGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<SkillInfo | null>(null);
  const [selectedSkillNames, setSelectedSkillNames] = useState<Set<string>>(
    new Set()
  );

  useEffect(() => {
    setLoading(true);
    api
      .request<{ groups: SkillGroup[] }>("/skills", token)
      .then((data) => {
        setGroups(data.groups);
        // Expand first group by default
        if (data.groups.length > 0) {
          setExpandedGroup(data.groups[0].name);
        }
      })
      .catch(() => setGroups([]))
      .finally(() => setLoading(false));
  }, [token]);

  const toggleGroup = (name: string) => {
    setExpandedGroup((prev) => (prev === name ? null : name));
  };

  const toggleSkill = (skill: SkillInfo) => {
    setSelectedSkillNames((prev) => {
      const next = new Set(prev);
      if (next.has(skill.name)) {
        next.delete(skill.name);
      } else {
        next.add(skill.name);
      }
      return next;
    });
  };

  if (loading) {
    return (
      <div className="p-6 text-sm text-surface-400 text-center">{t("skillBrowser.loading")}</div>
    );
  }

  if (groups.length === 0) {
    return (
      <div className="p-6 text-sm text-surface-400 text-center">
        {t("skillBrowser.noSkills")}
        <br />
        <span className="text-xs">
          {t("skillBrowser.addYaml")} <code className="bg-surface-100 px-1.5 py-0.5 rounded-lg">skills/</code> {t("skillBrowser.directory")}
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Selected count indicator (header removed — section header in Layout provides label) */}
      {selectedSkillNames.size > 0 && (
        <div className="px-3 py-1.5 text-xs text-brand-500 shrink-0">
          {selectedSkillNames.size} {t("skillBrowser.selected")}
        </div>
      )}

      {/* Group list */}
      <div className="flex-1 overflow-y-auto">
        {groups.map((group) => {
          const isExpanded = expandedGroup === group.name;
          return (
            <div key={group.name}>
              {/* Group header */}
              <button
                onClick={() => toggleGroup(group.name)}
                className="w-full flex items-center gap-2 mx-1 px-3 py-2 text-sm font-semibold text-surface-600 hover:bg-surface-50 rounded-xl transition-all duration-200 ease-out"
              >
                <svg
                  className={`w-3.5 h-3.5 shrink-0 transition-transform duration-200 text-surface-400 ${
                    isExpanded ? "rotate-90" : ""
                  }`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
                <span className="truncate capitalize">{group.name}</span>
                <span className="text-xs text-surface-400 ml-auto">
                  {group.skills.length}
                </span>
              </button>

              {/* Skill list */}
              {isExpanded && (
                <div className="ml-3 border-l border-surface-200/60">
                  {group.skills.map((skill) => (
                    <div key={skill.name}>
                      <button
                        onClick={() => {
                          toggleSkill(skill);
                          setSelectedSkill(
                            selectedSkill?.name === skill.name
                              ? null
                              : skill
                          );
                        }}
                        className={`w-full text-left px-3 py-1.5 text-sm transition-all duration-200 ease-out rounded-lg ${
                          selectedSkillNames.has(skill.name)
                            ? "bg-brand-50 text-brand-700"
                            : "text-surface-600 hover:bg-surface-50"
                        }`}
                      >
                        <div className="flex items-center gap-1.5">
                          {selectedSkillNames.has(skill.name) && (
                            <svg
                              className="w-3.5 h-3.5 text-brand-500 shrink-0"
                              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                          <span className="truncate">
                            {skill.display_name}
                          </span>
                        </div>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
