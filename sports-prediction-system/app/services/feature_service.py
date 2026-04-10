class FeatureService:
    def _calculate_form_score(self, recent_matches, team_name):
        if not recent_matches: return 50.0
        points=0; counted=0
        for m in recent_matches[:5]:
            ht=m.get('homeTeam',{}).get('name',''); at=m.get('awayTeam',{}).get('name',''); hs=m.get('homeScore',{}).get('current'); a=m.get('awayScore',{}).get('current')
            if hs is None or a is None: continue
            counted += 1
            if ht == team_name:
                if hs > a: points += 3
                elif hs == a: points += 1
            elif at == team_name:
                if a > hs: points += 3
                elif a == hs: points += 1
        return 50.0 if counted == 0 else (points/(counted*3))*100
    def _calculate_h2h_ratio(self,h2h_matches,home_team,away_team):
        if not h2h_matches: return 0.5
        home_wins=0; total=0
        for m in h2h_matches[:10]:
            ht=m.get('homeTeam',{}).get('name',''); at=m.get('awayTeam',{}).get('name',''); hs=m.get('homeScore',{}).get('current'); a=m.get('awayScore',{}).get('current')
            if hs is None or a is None: continue
            total += 1
            if ht == home_team and hs > a: home_wins += 1
            elif at == home_team and a > hs: home_wins += 1
        return 0.5 if total == 0 else home_wins/total
    def _calculate_goals_stats(self,recent_matches,team_name):
        scored=[]; conceded=[]
        for m in recent_matches[:5]:
            ht=m.get('homeTeam',{}).get('name',''); at=m.get('awayTeam',{}).get('name',''); hs=m.get('homeScore',{}).get('current'); a=m.get('awayScore',{}).get('current')
            if hs is None or a is None: continue
            if ht == team_name: scored.append(hs); conceded.append(a)
            elif at == team_name: scored.append(a); conceded.append(hs)
        return {'avg_scored': sum(scored)/len(scored) if scored else 0.0, 'avg_conceded': sum(conceded)/len(conceded) if conceded else 0.0}
    def extract(self, match_data, home_team, away_team):
        fh=self._calculate_form_score(match_data.get('home_recent',[]),home_team); fa=self._calculate_form_score(match_data.get('away_recent',[]),away_team); h2h=self._calculate_h2h_ratio(match_data.get('h2h',[]),home_team,away_team); hg=self._calculate_goals_stats(match_data.get('home_recent',[]),home_team); ag=self._calculate_goals_stats(match_data.get('away_recent',[]),away_team); stats_diff=((fh-fa)*0.5 + ((hg['avg_scored']-ag['avg_scored'])*10)*0.5)
        return {'form_home':fh,'form_away':fa,'h2h_home_ratio':h2h,'home_advantage':1.0,'goals_scored_home':hg['avg_scored'],'goals_conceded_home':hg['avg_conceded'],'goals_scored_away':ag['avg_scored'],'goals_conceded_away':ag['avg_conceded'],'derived_stats_balance':stats_diff,'stats_diff':stats_diff,'xg_diff':0.0,'xg_available':0.0,'data_quality':match_data.get('data_quality',0.0)}
_feature_service=None
def get_feature_service():
    global _feature_service
    if _feature_service is None: _feature_service=FeatureService()
    return _feature_service
