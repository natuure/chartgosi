const rankings = [
  { rank: 1, nickname: "차트마스터", score: 1200, accuracy: 92 },
  { rank: 2, nickname: "봉의달인", score: 1140, accuracy: 89 },
  { rank: 3, nickname: "추세추종자", score: 1088, accuracy: 86 },
];

export default function RankingsPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8 text-white">
      <div className="mx-auto max-w-4xl">
        <h1 className="text-4xl font-black">랭킹</h1>
        <div className="mt-8 overflow-hidden rounded-2xl border border-white/10 bg-white/8">
          {rankings.map((user) => (
            <div key={user.rank} className="grid grid-cols-[80px_1fr_100px_100px] gap-4 border-b border-white/10 p-5 last:border-b-0">
              <strong className="text-cyan-300">#{user.rank}</strong>
              <span>{user.nickname}</span>
              <span>{user.score}점</span>
              <span>{user.accuracy}%</span>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
