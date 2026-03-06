import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getRequirement, updateRequirement } from '../api/requirements';
import { startPipeline, runExtraction, runSearch, runRanking } from '../api/pipeline';
import type { ExtractedRequirement, RequirementUpdate } from '../types/requirement';
import ConfidenceBadge from '../components/requirements/ConfidenceBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorAlert from '../components/common/ErrorAlert';

const PROPERTY_TYPE_OPTIONS = [
  'Detached',
  'Semi-detached',
  'Freehold townhouse',
  'Condo townhouse',
  'Condo apartment',
  'Linked',
];

const GARAGE_TYPE_OPTIONS = [
  { value: '', label: 'Any' },
  { value: 'attached', label: 'Attached' },
  { value: 'detached', label: 'Detached' },
];

export default function RequirementsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [req, setReq] = useState<ExtractedRequirement | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<RequirementUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runningPipeline, setRunningPipeline] = useState(false);
  const [pipelineStage, setPipelineStage] = useState<string | null>(null);

  const initForm = (data: ExtractedRequirement): RequirementUpdate => ({
    client_name: data.client_name || '',
    budget_max: data.budget_max || 0,
    locations: data.locations,
    must_haves: data.must_haves,
    nice_to_haves: data.nice_to_haves,
    property_type: data.property_type || '',
    property_types: data.property_types || [],
    min_beds: data.min_beds || 0,
    min_baths: data.min_baths || 0,
    min_full_baths: data.min_full_baths || 0,
    min_total_baths: data.min_total_baths || 0,
    min_sqft: data.min_sqft || 0,
    min_total_parking: data.min_total_parking || 0,
    min_garage_spaces: data.min_garage_spaces || 0,
    garage_type: data.garage_type || '',
    basement_required: data.basement_required || false,
    basement_finished: data.basement_finished || false,
    basement_separate_entrance: data.basement_separate_entrance || false,
    basement_legal_suite: data.basement_legal_suite || false,
    city: data.city || '',
    sub_area: data.sub_area || '',
    school_requirement: data.school_requirement || '',
    timeline: data.timeline || '',
    financing_type: data.financing_type || '',
  });

  useEffect(() => {
    async function load() {
      try {
        const data = await getRequirement(Number(id));
        setReq(data);
        setForm(initForm(data));
      } catch {
        setError('Failed to load requirements.');
      } finally {
        setLoading(false);
      }
    }
    load();
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

  const handleRunPipeline = async () => {
    if (!req) return;
    setRunningPipeline(true);
    setError(null);
    try {
      setPipelineStage('Starting pipeline...');
      const run = await startPipeline(req.transcript_id);

      setPipelineStage('Extracting requirements...');
      await runExtraction(run.id);

      setPipelineStage('Searching listings...');
      await runSearch(run.id);

      setPipelineStage('Ranking results...');
      await runRanking(run.id);

      navigate(`/pipeline/${run.id}/search`);
    } catch {
      setError('Pipeline failed. Please try again.');
    } finally {
      setRunningPipeline(false);
      setPipelineStage(null);
    }
  };

  const updateList = (key: keyof RequirementUpdate, index: number, value: string) => {
    const list = [...((form[key] as string[]) || [])];
    list[index] = value;
    setForm({ ...form, [key]: list });
  };

  const addToList = (key: keyof RequirementUpdate) => {
    const list = [...((form[key] as string[]) || []), ''];
    setForm({ ...form, [key]: list });
  };

  const removeFromList = (key: keyof RequirementUpdate, index: number) => {
    const list = ((form[key] as string[]) || []).filter((_, i) => i !== index);
    setForm({ ...form, [key]: list });
  };

  const togglePropertyType = (type: string) => {
    const current = form.property_types || [];
    const updated = current.includes(type)
      ? current.filter((t) => t !== type)
      : [...current, type];
    setForm({ ...form, property_types: updated });
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
          onClick={() => (editing ? handleSave() : setEditing(true))}
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

      {runningPipeline && (
        <div className="border border-ink bg-surface p-8 flex flex-col items-center gap-4">
          <div className="h-6 w-6 animate-spin border-2 border-ink border-t-transparent" />
          <p className="text-[11px] uppercase tracking-[1px] opacity-70">
            {pipelineStage || 'Running pipeline...'}
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Client Info */}
        <section className="border border-ink bg-surface">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Client Info
          </div>
          <div className="p-4 space-y-3">
            <Field label="Name" value={editing ? form.client_name : req.client_name} editing={editing} onChange={(v) => setForm({ ...form, client_name: v })} />
            <Field label="Budget Max" value={editing ? String(form.budget_max) : req.budget_max ? `$${req.budget_max.toLocaleString()}` : '—'} editing={editing} onChange={(v) => setForm({ ...form, budget_max: Number(v) })} />
            <Field label="Timeline" value={editing ? form.timeline : req.timeline} editing={editing} onChange={(v) => setForm({ ...form, timeline: v })} />
            <Field label="Financing" value={editing ? form.financing_type : req.financing_type} editing={editing} onChange={(v) => setForm({ ...form, financing_type: v })} />
          </div>
        </section>

        {/* Property Details */}
        <section className="border border-ink bg-surface">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Property Details
          </div>
          <div className="p-4 space-y-3">
            <Field label="Type" value={editing ? form.property_type : req.property_type} editing={editing} onChange={(v) => setForm({ ...form, property_type: v })} />
            <Field label="Min Beds" value={editing ? String(form.min_beds) : String(req.min_beds || 'Any')} editing={editing} onChange={(v) => setForm({ ...form, min_beds: Number(v) })} />
            <Field label="Min Baths" value={editing ? String(form.min_baths) : String(req.min_baths || 'Any')} editing={editing} onChange={(v) => setForm({ ...form, min_baths: Number(v) })} />
            <Field label="Min Sqft" value={editing ? String(form.min_sqft) : req.min_sqft ? req.min_sqft.toLocaleString() : 'Any'} editing={editing} onChange={(v) => setForm({ ...form, min_sqft: Number(v) })} />
            <Field label="School Req" value={editing ? form.school_requirement : req.school_requirement} editing={editing} onChange={(v) => setForm({ ...form, school_requirement: v })} />
          </div>
        </section>

        {/* Property Types */}
        <section className="border border-ink bg-surface">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Property Types
          </div>
          <div className="p-4">
            {editing ? (
              <div className="space-y-2">
                {PROPERTY_TYPE_OPTIONS.map((type) => (
                  <label key={type} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={(form.property_types || []).includes(type)}
                      onChange={() => togglePropertyType(type)}
                      className="w-4 h-4 accent-ink cursor-pointer"
                    />
                    <span className="text-[12px]">{type}</span>
                  </label>
                ))}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {(req.property_types || []).length === 0 ? (
                  <p className="text-[11px] uppercase opacity-40">None</p>
                ) : (
                  req.property_types.map((type, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center px-3 py-1 rounded-full text-[10px] uppercase border border-ink"
                    >
                      {type}
                    </span>
                  ))
                )}
              </div>
            )}
          </div>
        </section>

        {/* Bathrooms */}
        <section className="border border-ink bg-surface">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Bathrooms
          </div>
          <div className="p-4 space-y-3">
            <NumberField
              label="Min Full Baths"
              value={editing ? (form.min_full_baths ?? 0) : (req.min_full_baths ?? 0)}
              editing={editing}
              onChange={(v) => setForm({ ...form, min_full_baths: v })}
            />
            <NumberField
              label="Min Total Baths"
              value={editing ? (form.min_total_baths ?? 0) : (req.min_total_baths ?? 0)}
              editing={editing}
              onChange={(v) => setForm({ ...form, min_total_baths: v })}
            />
          </div>
        </section>

        {/* Parking */}
        <section className="border border-ink bg-surface">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Parking
          </div>
          <div className="p-4 space-y-3">
            <NumberField
              label="Min Total Parking"
              value={editing ? (form.min_total_parking ?? 0) : (req.min_total_parking ?? 0)}
              editing={editing}
              onChange={(v) => setForm({ ...form, min_total_parking: v })}
            />
            <NumberField
              label="Min Garage Spaces"
              value={editing ? (form.min_garage_spaces ?? 0) : (req.min_garage_spaces ?? 0)}
              editing={editing}
              onChange={(v) => setForm({ ...form, min_garage_spaces: v })}
            />
            <div className="flex items-center gap-2 border-b border-ink/10 pb-2">
              <span className="text-[10px] uppercase tracking-[1px] opacity-50 w-24 shrink-0">Garage Type</span>
              {editing ? (
                <select
                  value={form.garage_type || ''}
                  onChange={(e) => setForm({ ...form, garage_type: e.target.value })}
                  className="flex-1 border border-ink bg-transparent px-2 py-1 text-[12px] focus:outline-none focus:ring-1 focus:ring-ink cursor-pointer"
                >
                  {GARAGE_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              ) : (
                <span className="font-heading text-[16px]">
                  {req.garage_type ? req.garage_type.charAt(0).toUpperCase() + req.garage_type.slice(1) : 'Any'}
                </span>
              )}
            </div>
          </div>
        </section>

        {/* Basement */}
        <section className="border border-ink bg-surface">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Basement
          </div>
          <div className="p-4 space-y-3">
            <BooleanField
              label="Required"
              value={editing ? (form.basement_required ?? false) : (req.basement_required ?? false)}
              editing={editing}
              onChange={(v) => setForm({ ...form, basement_required: v })}
            />
            <BooleanField
              label="Finished"
              value={editing ? (form.basement_finished ?? false) : (req.basement_finished ?? false)}
              editing={editing}
              onChange={(v) => setForm({ ...form, basement_finished: v })}
            />
            <BooleanField
              label="Sep. Entrance"
              value={editing ? (form.basement_separate_entrance ?? false) : (req.basement_separate_entrance ?? false)}
              editing={editing}
              onChange={(v) => setForm({ ...form, basement_separate_entrance: v })}
            />
            <BooleanField
              label="Legal Suite"
              value={editing ? (form.basement_legal_suite ?? false) : (req.basement_legal_suite ?? false)}
              editing={editing}
              onChange={(v) => setForm({ ...form, basement_legal_suite: v })}
            />
          </div>
        </section>

        {/* Locations */}
        <section className="border border-ink bg-surface">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Locations
          </div>
          <div className="p-4 space-y-4">
            <div className="space-y-3">
              <Field label="City" value={editing ? form.city : req.city} editing={editing} onChange={(v) => setForm({ ...form, city: v })} />
              <Field label="Sub-area" value={editing ? form.sub_area : req.sub_area} editing={editing} onChange={(v) => setForm({ ...form, sub_area: v })} />
            </div>
            <div className="border-t border-ink/10 pt-3">
              <span className="text-[10px] uppercase tracking-[1px] opacity-50 block mb-2">Preferred Areas</span>
              <TagList
                items={editing ? (form.locations || []) : req.locations}
                editing={editing}
                color="default"
                onChange={(i, v) => updateList('locations', i, v)}
                onAdd={() => addToList('locations')}
                onRemove={(i) => removeFromList('locations', i)}
              />
            </div>
          </div>
        </section>

        {/* Must-Haves */}
        <section className="border border-ink bg-accent-orange/10">
          <div className="p-4 border-b border-ink font-heading uppercase text-[14px]">
            Must-Haves (Deal Breakers)
          </div>
          <div className="p-4">
            <TagList
              items={editing ? (form.must_haves || []) : req.must_haves}
              editing={editing}
              color="orange"
              onChange={(i, v) => updateList('must_haves', i, v)}
              onAdd={() => addToList('must_haves')}
              onRemove={(i) => removeFromList('must_haves', i)}
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
              items={editing ? (form.nice_to_haves || []) : req.nice_to_haves}
              editing={editing}
              color="green"
              onChange={(i, v) => updateList('nice_to_haves', i, v)}
              onAdd={() => addToList('nice_to_haves')}
              onRemove={(i) => removeFromList('nice_to_haves', i)}
            />
          </div>
        </section>
      </div>

      {/* Pipeline Actions */}
      <div className="border border-ink bg-surface p-6 flex flex-col items-center gap-4">
        <p className="text-[11px] uppercase tracking-[1px] opacity-50">
          Ready to find matching properties?
        </p>
        <div className="flex gap-4">
          <button
            onClick={handleRunPipeline}
            disabled={runningPipeline}
            className="px-6 py-3 bg-ink text-surface text-[12px] uppercase tracking-[1px] cursor-pointer hover:opacity-80 transition-opacity disabled:opacity-50"
          >
            {runningPipeline ? 'Running...' : 'Run Pipeline'}
          </button>
          <button
            onClick={handleRunPipeline}
            disabled={runningPipeline}
            className="px-6 py-3 bg-accent-green text-ink text-[12px] uppercase tracking-[1px] border border-ink cursor-pointer hover:opacity-80 transition-opacity disabled:opacity-50"
          >
            {runningPipeline ? 'Generating...' : 'Generate Matches'}
          </button>
        </div>
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
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 border border-ink bg-transparent px-2 py-1 text-[12px] focus:outline-none focus:ring-1 focus:ring-ink"
        />
      ) : (
        <span className="font-heading text-[16px]">{value || '—'}</span>
      )}
    </div>
  );
}

function NumberField({
  label,
  value,
  editing,
  onChange,
}: {
  label: string;
  value: number;
  editing: boolean;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center gap-2 border-b border-ink/10 pb-2">
      <span className="text-[10px] uppercase tracking-[1px] opacity-50 w-24 shrink-0">{label}</span>
      {editing ? (
        <input
          type="number"
          min={0}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-20 border border-ink bg-transparent px-2 py-1 text-[12px] focus:outline-none focus:ring-1 focus:ring-ink"
        />
      ) : (
        <span className="font-heading text-[16px]">{value || 'Any'}</span>
      )}
    </div>
  );
}

function BooleanField({
  label,
  value,
  editing,
  onChange,
}: {
  label: string;
  value: boolean;
  editing: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center gap-2 border-b border-ink/10 pb-2">
      <span className="text-[10px] uppercase tracking-[1px] opacity-50 w-24 shrink-0">{label}</span>
      {editing ? (
        <button
          type="button"
          onClick={() => onChange(!value)}
          className={`w-10 h-5 rounded-full relative cursor-pointer transition-colors ${
            value ? 'bg-accent-green' : 'bg-ink/20'
          }`}
        >
          <span
            className={`block w-4 h-4 rounded-full bg-ink absolute top-0.5 transition-transform ${
              value ? 'translate-x-5' : 'translate-x-0.5'
            }`}
          />
        </button>
      ) : (
        <span className="font-heading text-[16px]">{value ? 'Yes' : 'No'}</span>
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
            onChange={(e) => onChange(i, e.target.value)}
            className="flex-1 border border-ink bg-transparent px-2 py-1 text-[12px] focus:outline-none focus:ring-1 focus:ring-ink"
          />
          <button
            onClick={() => onRemove(i)}
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
