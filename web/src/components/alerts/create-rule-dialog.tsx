"use client";

import { useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";

const schema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  schedule: z.enum(["daily", "weekly", "monthly"]),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface CreateRuleDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function CreateRuleDialog({ open, onClose, onCreated }: CreateRuleDialogProps) {
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { schedule: "daily" },
  });

  const scheduleValue = watch("schedule");

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    setServerError(null);
    try {
      await api.post("/api/alerts/rules", values);
      reset();
      onCreated();
      onClose();
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Failed to create rule");
    } finally {
      setSubmitting(false);
    }
  }

  function handleClose() {
    reset();
    setServerError(null);
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose(); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base font-semibold text-slate-900">
            Create Alert Rule
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <Label htmlFor="rule-name">Name</Label>
            <Input
              id="rule-name"
              placeholder="e.g. High cancellation rate"
              {...register("name")}
            />
            {errors.name && (
              <p className="text-xs text-red-600">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="rule-schedule">Schedule</Label>
            <Select
              value={scheduleValue}
              onValueChange={(val) => setValue("schedule", val as FormValues["schedule"])}
            >
              <SelectTrigger id="rule-schedule">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Daily (9 AM IST)</SelectItem>
                <SelectItem value="weekly">Weekly (Monday 9 AM IST)</SelectItem>
                <SelectItem value="monthly">Monthly (1st of month)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="rule-description">Description (optional)</Label>
            <Textarea
              id="rule-description"
              placeholder="Describe when this alert should fire..."
              rows={3}
              {...register("description")}
            />
          </div>

          {serverError && (
            <p className="text-xs text-red-600">{serverError}</p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={submitting}>
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-teal-600 hover:bg-teal-700 text-white"
              disabled={submitting}
            >
              {submitting ? "Creating..." : "Create Rule"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
