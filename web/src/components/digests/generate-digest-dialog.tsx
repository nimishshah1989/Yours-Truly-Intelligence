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
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";

const schema = z.object({
  digest_type: z.enum(["daily", "weekly", "monthly"]),
  date: z.string().min(1, "Please provide a date"),
});

type FormValues = z.infer<typeof schema>;

interface GenerateDigestDialogProps {
  open: boolean;
  onClose: () => void;
  onGenerated: () => void;
}

export function GenerateDigestDialog({
  open,
  onClose,
  onGenerated,
}: GenerateDigestDialogProps) {
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
    defaultValues: {
      digest_type: "daily",
      date: new Date().toISOString().split("T")[0],
    },
  });

  const typeValue = watch("digest_type");

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    setServerError(null);
    try {
      await api.post("/api/digests/generate", values);
      reset();
      onGenerated();
      onClose();
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Failed to generate digest");
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
            Generate Digest
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <Label htmlFor="digest-type">Digest Type</Label>
            <Select
              value={typeValue}
              onValueChange={(val) => setValue("digest_type", val as FormValues["digest_type"])}
            >
              <SelectTrigger id="digest-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="digest-date">Date</Label>
            <Input
              id="digest-date"
              type="date"
              {...register("date")}
            />
            {errors.date && (
              <p className="text-xs text-red-600">{errors.date.message}</p>
            )}
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
              {submitting ? "Generating..." : "Generate"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
