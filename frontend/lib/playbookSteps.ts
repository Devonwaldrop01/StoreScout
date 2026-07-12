/**
 * Playbook step-progress counting.
 *
 * Step completion is persisted per play-id in localStorage as a boolean[]. When
 * a playbook is regenerated a play's step list can shrink while an older, longer
 * `checked` array is still stored — counting the raw array then produces an
 * impossible ratio like "8/3". Completion is only ever counted over the steps
 * that currently exist.
 */
export function countDoneSteps(checked: boolean[] | undefined | null, stepCount: number): number {
  if (!checked || stepCount <= 0) return 0;
  let n = 0;
  for (let i = 0; i < stepCount; i++) if (checked[i]) n += 1;
  return n;
}
