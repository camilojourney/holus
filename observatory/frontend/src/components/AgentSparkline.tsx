'use client';

import { SparkBarChart } from '@tremor/react';

interface Props {
  scores: number[];
}

export default function AgentSparkline({ scores }: Props) {
  const chartData = scores.map((score, i) => ({
    index: String(i),
    Score: score,
  }));

  return (
    <SparkBarChart
      data={chartData}
      index="index"
      categories={['Score']}
      colors={['emerald']}
      className="h-16"
    />
  );
}
