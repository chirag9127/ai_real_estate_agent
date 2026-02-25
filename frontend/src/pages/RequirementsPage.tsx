import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getRequirement, updateRequirement } from '../api/requirements';
import ErrorAlert from '../components/common/ErrorAlert';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ConfidenceBadge from '../components/requirements/ConfidenceBadge';
import type { ExtractedRequirement, RequirementUpdate } from '../types/requirement';

export default function RequirementsPage() {
  const { id } = useParams<{ id: string }>();
  const [req, setReq] = useState<ExtractedRequirement | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<RequirementUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getRequirement(Number(id));
        setReq(data);
        setForm({
          client_name: data.client_name ?? '',
          budget_max: data.budget_max ?? 0,
          locations: data.locations,
          must_haves: data.must_haves,
          nice_to_haves: data.nice_to_haves,
          property_type: data.property_type ?? '',
          min_beds: data.min_beds ?? 0,
          min_baths: data.min_baths ?? 0,
          min_sqft: data.min_sqft ?? 0,
          school_requirement: data.school_requirement ?? '',
          timeline: data.timeline ?? '',
          financing_type: data.financing_type ?? '',
        });
      } catch {
        setError('Failed to load requirements.');
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [id]);

  const handleSave = async () => {
    if (!req) return;
    setSaving(true);
    try {
      const updated = await updateRequirement(req.id, form);
      setReq(updated);
      setEditing(false);
    } catch {
      setError('Failed to save changes.');
    } finally {
      setSaving(false);
    }
  };

  const updateList = (key: keyof RequirementUpdate, index: number, value: string) => {
    const list = [...((form[key] as string[] | undefined) ?? [])];
    list[index] = value;
    setForm({ ...form, [key]: list });
  };

  const addToList = (key: keyof RequirementUpdate) => {
    const list = [...((form[key] as string[] | undefined) ?? []), ''];
    setForm({ ...form, [key]: list });
  };

  const removeFromList = (key: keyof RequirementUpdate, index: number) => {
    const list = ((form[key] as string[] | undefined) ?? []).filter((_, i) => i !== index);
    setForm({ ...form, [key]: list });
  };

  if (loading) return <LoadingSpinner />;
  if (error && !req) return <ErrorAlert message={error} />;
  if (!req) return <ErrorAlert message="Requirements not found." />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            to={`/transcripts/${req.transcript_id}`}
            className="text-[10px] uppercase tracking-[1px] opacity-50 hover:opacity-100 transition-opacity"
          >
            ← Back to Transcript
          </Link>
          <h1 className="font-heading text-[32px] uppercase mt-2">
            Extracted Requirements
          </h1>
          <div className="flex items-center gap-3 mt-2">
            <ConfidenceBadge score={req.confidence_score} />
            {req.is_edited && (
              <span className="text-[10px] uppercase opacity-50">Manually edited</span>
            )}
            {req.llm_provider && (
              <span className="text-[10px] uppercase opacity-40">
                via {req.llm_provider} / {req.llm_model}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={() => { if (editing) { void handleSave(); } else { setEditing(true); } }}
          disabled={saving}
          className={`px-4 py-2 text-[11px] uppercase tracking-[1px] cursor-pointer transition-colors disabled:opacity-50 ${
            editing
              ? 'bg-accent-green text-ink border border-ink'
              : 'border border-ink hover:bg-ink hover:text-surface'
          }`}
        >
          {saving ? 'Saving...' : editing ? 'Save Changes' : 'Edit'}
        </button>
      </div>

      {error && <ErrorAlert message={error} />}

      <div className="grid grid-cols-2 gap-6">
        {/* Client Info */}
        <section className="border border-ink bg-surface">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Client Info
          </div>
          <div className="p-4 space-y-3">
            <Field label="Name" value={editing ? form.client_name : req.client_name} editing={editing} onChange={(v) => { setForm({ ...form, client_name: v }); }} />
            <Field label="Budget Max" value={editing ? String(form.budget_max) : req.budget_max ? `$${req.budget_max.toLocaleString()}` : '—'} editing={editing} onChange={(v) => { setForm({ ...form, budget_max: Number(v) }); }} />
            <Field label="Timeline" value={editing ? form.timeline : req.timeline} editing={editing} onChange={(v) => { setForm({ ...form, timeline: v }); }} />
            <Field label="Financing" value={editing ? form.financing_type : req.financing_type} editing={editing} onChange={(v) => { setForm({ ...form, financing_type: v }); }} />
          </div>
        </section>

        {/* Property Details */}
        <section className="border border-ink bg-surface">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Property Details
          </div>
          <div className="p-4 space-y-3">
            <Field label="Type" value={editing ? form.property_type : req.property_type} editing={editing} onChange={(v) => { setForm({ ...form, property_type: v }); }} />
            <Field label="Min Beds" value={editing ? String(form.min_beds) : String(req.min_beds ?? 'Any')} editing={editing} onChange={(v) => { setForm({ ...form, min_beds: Number(v) }); }} />
            <Field label="Min Baths" value={editing ? String(form.min_baths) : String(req.min_baths ?? 'Any')} editing={editing} onChange={(v) => { setForm({ ...form, min_baths: Number(v) }); }} />
            <Field label="Min Sqft" value={editing ? String(form.min_sqft) : req.min_sqft ? req.min_sqft.toLocaleString() : 'Any'} editing={editing} onChange={(v) => { setForm({ ...form, min_sqft: Number(v) }); }} />
            <Field label="School Req" value={editing ? form.school_requirement : req.school_requirement} editing={editing} onChange={(v) => { setForm({ ...form, school_requirement: v }); }} />
          </div>
        </section>

        {/* Locations */}
        <section className="border border-ink bg-surface">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Locations
          </div>
          <div className="p-4">
            <TagList
              items={editing ? (form.locations ?? []) : req.locations}
              editing={editing}
              color="default"
              onChange={(i, v) => { updateList('locations', i, v); }}
              onAdd={() => { addToList('locations'); }}
              onRemove={(i) => { removeFromList('locations', i); }}
            />
          </div>
        </section>

        {/* Must-Haves */}
        <section className="border border-ink bg-accent-orange/10">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Must-Haves (Deal Breakers)
          </div>
          <div className="p-4">
            <TagList
              items={editing ? (form.must_haves ?? []) : req.must_haves}
              editing={editing}
              color="orange"
              onChange={(i, v) => { updateList('must_haves', i, v); }}
              onAdd={() => { addToList('must_haves'); }}
              onRemove={(i) => { removeFromList('must_haves', i); }}
            />
          </div>
        </section>

        {/* Nice-to-Haves */}
        <section className="col-span-2 border border-ink bg-accent-green/10">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Nice-to-Haves
          </div>
          <div className="p-4">
            <TagList
              items={editing ? (form.nice_to_haves ?? []) : req.nice_to_haves}
              editing={editing}
              color="green"
              onChange={(i, v) => { updateList('nice_to_haves', i, v); }}
              onAdd={() => { addToList('nice_to_haves'); }}
              onRemove={(i) => { removeFromList('nice_to_haves', i); }}
            />
          </div>
        </section>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  editing,
  onChange,
}: {
  label: string;
  value: string | null | undefined;
  editing: boolean;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-2 border-b border-ink/10 pb-2">
      <span className="text-[10px] uppercase tracking-[1px] opacity-50 w-24 shrink-0">{label}</span>
      {editing ? (
        <input
          type="text"
          value={value ?? ''}
          onChange={(e) => { onChange(e.target.value); }}
          className="flex-1 border border-ink bg-transparent px-2 py-1 text-[12px] focus:outline-none focus:ring-1 focus:ring-ink"
        />
      ) : (
        <span className="font-heading text-[16px]">{value ?? '—'}</span>
      )}
    </div>
  );
}

const tagStyles: Record<string, string> = {
  default: 'border-ink',
  orange: 'border-accent-orange bg-accent-orange text-ink',
  green: 'border-accent-green bg-accent-green text-ink',
};

function TagList({
  items,
  editing,
  color,
  onChange,
  onAdd,
  onRemove,
}: {
  items: string[];
  editing: boolean;
  color: string;
  onChange: (index: number, value: string) => void;
  onAdd: () => void;
  onRemove: (index: number) => void;
}) {
  if (!editing) {
    if (items.length === 0) return <p className="text-[11px] uppercase opacity-40">None</p>;
    return (
      <div className="flex flex-wrap gap-2">
        {items.map((item, i) => (
          <span
            key={i}
            className={`inline-flex items-center px-3 py-1 rounded-full text-[10px] uppercase border ${tagStyles[color]}`}
          >
            {item}
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <div key={i} className="flex items-center gap-2">
          <input
            type="text"
            value={item}
            onChange={(e) => { onChange(i, e.target.value); }}
            className="flex-1 border border-ink bg-transparent px-2 py-1 text-[12px] focus:outline-none focus:ring-1 focus:ring-ink"
          />
          <button
            onClick={() => { onRemove(i); }}
            className="w-6 h-6 border border-ink rounded-full text-[10px] flex items-center justify-center cursor-pointer hover:bg-ink hover:text-surface transition-colors"
          >
            ×
          </button>
        </div>
      ))}
      <button
        onClick={onAdd}
        className="text-[10px] uppercase tracking-[1px] border border-ink px-3 py-1 rounded-full cursor-pointer hover:bg-ink hover:text-surface transition-colors"
      >
        + Add Item
      </button>
    </div>
  );
}
