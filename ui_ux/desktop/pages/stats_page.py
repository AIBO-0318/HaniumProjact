"""
I-Study - 학습 통계 페이지
집중도 추이, 학습 기록, 방해 요소 타임라인을 표시합니다.
"""

import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from shared.config import (
    BG_COLOR, CARD_BG, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    GREEN, RED, BLUE, PURPLE, ORANGE, ACCENT_YELLOW
)


class StatsPage:
    """학습 통계 페이지 빌더"""

    def __init__(self, app):
        self.app = app

    def create(self) -> ctk.CTkScrollableFrame:
        """학습 통계 페이지 프레임 생성 및 반환"""
        app = self.app
        page = ctk.CTkScrollableFrame(app, fg_color=BG_COLOR, corner_radius=0)

        # 헤더
        header = ctk.CTkFrame(page, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(25, 3))
        ctk.CTkLabel(header, text="학습 통계 📊", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        ctk.CTkLabel(page, text="내 집중도 패턴을 분석하고 더 똑똑하게 공부하세요", font=ctk.CTkFont(size=13), text_color=TEXT_SECONDARY).pack(anchor="w", padx=30, pady=(0, 15))

        # 통계 카드 행
        stats_row = ctk.CTkFrame(page, fg_color="transparent")
        stats_row.pack(fill="x", padx=30, pady=10)
        for i in range(4):
            stats_row.grid_columnconfigure(i, weight=1)

        today_focus = app.db.get_today_total_focus_time()
        th, tr = divmod(today_focus, 3600)
        tm, _ = divmod(tr, 60)

        logs = app.db.get_study_logs(limit=30)
        total_focus_all = sum(l.get('focus_time_seconds', 0) for l in logs) if logs else 0
        total_time_all = sum(l.get('total_time_seconds', 0) for l in logs) if logs else 0
        avg_score = int(total_focus_all / total_time_all * 100) if total_time_all > 0 else 0
        best_score = avg_score

        stat_items = [
            ("🎯", f"{avg_score}점", "평균 집중도", RED, "↗ 향상 중!"),
            ("⭐", f"{best_score}점", "최고 집중도", ACCENT_YELLOW, "오늘 최고 기록"),
            ("📚", f"{th}h {tm}m", "오늘 학습", BLUE, f"목표 80% 달성"),
            ("🚫", f"{app.block_count}회", "방해 차단", PURPLE, "집중력 향상!"),
        ]
        app.stats_page_labels = {}
        for idx, (icon, val, label, color, sub) in enumerate(stat_items):
            card = ctk.CTkFrame(stats_row, fg_color=CARD_BG, corner_radius=16)
            card.grid(row=0, column=idx, sticky="nsew", padx=5)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(padx=15, pady=15)
            ctk.CTkLabel(inner, text=icon, font=ctk.CTkFont(size=22)).pack(anchor="w")
            v = ctk.CTkLabel(inner, text=val, font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT_PRIMARY)
            v.pack(anchor="w", pady=(5, 0))
            ctk.CTkLabel(inner, text=label, font=ctk.CTkFont(size=11), text_color=TEXT_SECONDARY).pack(anchor="w")
            ctk.CTkLabel(inner, text=sub, font=ctk.CTkFont(size=10), text_color=color).pack(anchor="w", pady=(3, 0))
            app.stats_page_labels[label] = v

        # 집중도 추이 그래프
        graph_card = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=20)
        graph_card.pack(fill="x", padx=30, pady=10)

        graph_header = ctk.CTkFrame(graph_card, fg_color="transparent")
        graph_header.pack(fill="x", padx=25, pady=(20, 10))
        ctk.CTkLabel(graph_header, text="📈 집중도 추이", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        app.graph_frame = ctk.CTkFrame(graph_card, fg_color="#F8F8F8", corner_radius=12)
        app.graph_frame.pack(fill="both", padx=15, pady=(0, 15), expand=True)

        self._create_focus_graph()

        # 학습 기록 리스트
        log_card = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=20)
        log_card.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(log_card, text="📋 학습 기록", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=25, pady=(20, 10))

        app.log_list_frame = ctk.CTkScrollableFrame(log_card, fg_color="transparent", height=200)
        app.log_list_frame.pack(fill="both", padx=15, pady=(0, 15), expand=True)

        self._refresh_stats_logs()

        # 방해 요소 타임라인
        timeline_card = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=20)
        timeline_card.pack(fill="x", padx=30, pady=10)

        tl_header = ctk.CTkFrame(timeline_card, fg_color="transparent")
        tl_header.pack(fill="x", padx=25, pady=(20, 10))
        ctk.CTkLabel(tl_header, text="⚡ 방해 요소 타임라인", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        legend = ctk.CTkFrame(tl_header, fg_color="transparent")
        legend.pack(side="right")
        for lbl, clr in [("시선 이탈", RED), ("눈 감음", ORANGE), ("URL 차단", PURPLE)]:
            ctk.CTkLabel(legend, text=f"● {lbl}", font=ctk.CTkFont(size=10), text_color=clr).pack(side="left", padx=5)

        app.timeline_frame = ctk.CTkScrollableFrame(timeline_card, fg_color="transparent", height=120)
        app.timeline_frame.pack(fill="both", padx=15, pady=(0, 15), expand=True)
        ctk.CTkLabel(app.timeline_frame, text="아직 기록이 없습니다", font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).pack(pady=20)

        return page

    def _create_focus_graph(self):
        """집중도 추이 그래프 생성"""
        app = self.app
        try:
            for w in app.graph_frame.winfo_children():
                w.destroy()

            logs = app.db.get_study_logs(limit=14)

            if not logs:
                ctk.CTkLabel(
                    app.graph_frame,
                    text="학습 기록이 쌓이면 그래프가 표시됩니다",
                    font=ctk.CTkFont(size=12),
                    text_color=TEXT_MUTED
                ).pack(pady=40)
                return

            # 날짜별로 데이터 집계
            daily_data = {}
            for log in logs:
                date_str = log['study_date']
                if date_str not in daily_data:
                    daily_data[date_str] = {'total_time': 0, 'focus_time': 0}
                daily_data[date_str]['total_time'] += log['total_time_seconds']
                daily_data[date_str]['focus_time'] += log['focus_time_seconds']

            sorted_dates = sorted(daily_data.keys())

            dates = []
            focus_rates = []
            for full_date in sorted_dates:
                date_str = full_date[5:] if len(full_date) > 5 else full_date
                dates.append(date_str)
                total_time = daily_data[full_date]['total_time']
                focus_time = daily_data[full_date]['focus_time']
                rate = (focus_time / total_time * 100) if total_time > 0 else 0
                focus_rates.append(rate)

            fig = Figure(figsize=(10, 3.5), dpi=80, facecolor='#F8F8F8')
            ax = fig.add_subplot(111)

            ax.plot(dates, focus_rates, marker='o', linewidth=3, markersize=8,
                    color='#007AFF', markerfacecolor='#007AFF', markeredgecolor='white',
                    markeredgewidth=2.5, zorder=3)

            ax.fill_between(range(len(dates)), focus_rates, alpha=0.1, color='#007AFF', zorder=1)

            ax.set_ylim(0, 105)
            ax.set_ylabel('집중도 (%)', fontsize=11, color='#666666')
            ax.set_xlabel('날짜', fontsize=11, color='#666666')
            ax.set_title('최근 학습 집중도 추이', fontsize=13, weight='bold', color='#1A1A1A', pad=15)

            ax.grid(True, alpha=0.25, linestyle='--', linewidth=0.5, zorder=0)
            ax.set_facecolor('#F8F8F8')
            fig.patch.set_facecolor('#F8F8F8')

            ax.tick_params(colors='#666666', labelsize=9)
            for spine in ax.spines.values():
                spine.set_color('#DDDDDD')
                spine.set_linewidth(1)

            fig.tight_layout(pad=2)

            canvas = FigureCanvasTkAgg(fig, master=app.graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        except Exception as e:
            error_msg = f"그래프 생성 중 오류 발생:\n{str(e)}"
            ctk.CTkLabel(
                app.graph_frame,
                text=error_msg,
                font=ctk.CTkFont(size=12),
                text_color=RED
            ).pack(pady=40)
            print(f"Graph creation error: {e}")
            import traceback
            traceback.print_exc()

    def _refresh_stats_logs(self):
        """학습 기록 리스트 새로고침"""
        app = self.app
        for w in app.log_list_frame.winfo_children():
            w.destroy()

        logs = app.db.get_study_logs(limit=10)
        if not logs:
            ctk.CTkLabel(app.log_list_frame, text="학습 기록이 없습니다", font=ctk.CTkFont(size=13), text_color=TEXT_MUTED).pack(pady=30)
            return

        for log in logs:
            row = ctk.CTkFrame(app.log_list_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=5)

            total_h, total_r = divmod(log['total_time_seconds'], 3600)
            total_m, _ = divmod(total_r, 60)
            focus_h, focus_r = divmod(log['focus_time_seconds'], 3600)
            focus_m, _ = divmod(focus_r, 60)
            rate = int(log['focus_time_seconds'] / log['total_time_seconds'] * 100) if log['total_time_seconds'] > 0 else 0

            ctk.CTkLabel(row, text=log['study_date'], font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
            ctk.CTkLabel(row, text=f"총 {total_h}h {total_m}m | 집중 {focus_h}h {focus_m}m | {rate}%", font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY).pack(side="right")

            ctk.CTkFrame(app.log_list_frame, height=1, fg_color="#F0F0F0").pack(fill="x", padx=10, pady=2)

    def refresh(self):
        """통계 페이지 전체 새로고침"""
        self._create_focus_graph()
        self._refresh_stats_logs()
        self._update_stats_cards()

    def _update_stats_cards(self):
        """통계 카드 값 업데이트"""
        app = self.app
        logs = app.db.get_study_logs(limit=30)

        if not logs:
            return

        total_focus_time = sum(log['focus_time_seconds'] for log in logs)
        total_time = sum(log['total_time_seconds'] for log in logs)
        avg_focus = int(total_focus_time / total_time * 100) if total_time > 0 else 0

        max_focus = 0
        for log in logs:
            if log['total_time_seconds'] > 0:
                rate = int(log['focus_time_seconds'] / log['total_time_seconds'] * 100)
                max_focus = max(max_focus, rate)

        today_total = app.db.get_today_total_focus_time()
        today_h, today_r = divmod(today_total, 3600)
        today_m, _ = divmod(today_r, 60)

        if "평균 집중도" in app.stats_page_labels:
            app.stats_page_labels["평균 집중도"].configure(text=f"{avg_focus}%")
        if "최고 집중도" in app.stats_page_labels:
            app.stats_page_labels["최고 집중도"].configure(text=f"{max_focus}%")
        if "오늘 학습" in app.stats_page_labels:
            app.stats_page_labels["오늘 학습"].configure(text=f"{today_h}h {today_m}m")
