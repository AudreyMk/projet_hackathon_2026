"""
src/recommendations/citizen_actions.py
========================================
Moteur de préconisations citoyennes adaptatif.
Aligné avec : PNACC 3, Earth Action Report 2025, Neutralité carbone 2050.

Génère des recommandations contextualisées selon :
- Le score de risque climatique du territoire
- Les indicateurs de chaleur extrême
- Le déficit de précipitations
"""

from typing import Dict, List


class RecommendationEngine:
    """
    Génère des préconisations citoyennes et institutionnelles
    adaptées au profil climatique du territoire.

    Catégories :
    1. Risque feux de forêt
    2. Sécheresse et ressource en eau
    3. Canicules et îlots de chaleur
    4. Réduction empreinte carbone
    5. Adaptation du territoire
    """

    # Seuils déclencheurs
    SEUIL_RISQUE_ELEVE = 65
    SEUIL_CHALEUR_EXTREME = 25      # jours > 30°C / an
    SEUIL_SECHERESSE = -10          # % déficit précipitations

    def get_recommendations(
        self,
        risk_score: float,
        jours_chauds: float,
        deficit_precip: float,
        territoire: str = "France",
    ) -> Dict[str, List[Dict]]:
        """
        Génère les préconisations selon le profil de risque.

        Args:
            risk_score: Score de risque composite (0-100)
            jours_chauds: Nombre de jours > 30°C par an
            deficit_precip: Déficit précipitations vs normale (%)
            territoire: Nom du territoire

        Returns:
            Dict {catégorie: [{titre, description, impact, priority, source}]}
        """
        recs = {}

        # 1. Canicules (toujours pertinent)
        recs[" Faire face aux canicules"] = self._recs_canicule(jours_chauds, territoire)

        # 2. Sécheresse
        if deficit_precip < self.SEUIL_SECHERESSE or risk_score > 50:
            recs[" Gérer la sécheresse"] = self._recs_secheresse(deficit_precip)

        # 3. Feux de forêt
        if risk_score > self.SEUIL_RISQUE_ELEVE:
            recs[" Prévention incendies"] = self._recs_feux()

        # 4. Réduction carbone (toujours)
        recs[" Réduire son empreinte carbone"] = self._recs_carbone()

        # 5. Adaptation territoriale
        if risk_score > 40:
            recs[" Adapter son territoire"] = self._recs_adaptation(territoire)

        return recs

    # 
    # CANICULES
    # 
    def _recs_canicule(self, jours_chauds: float, territoire: str) -> List[Dict]:
        recs = [
            {
                "titre": "Végétalisation urbaine",
                "description": "Planter des arbres et créer des espaces verts pour réduire "
                               "les îlots de chaleur urbain. Objectif : +30% de canopée d'ici 2030.",
                "impact": "−2 à −4°C en milieu urbain",
                "priority": "haute",
                "source": "PNACC 3 · Axe 3",
            },
            {
                "titre": "Toits et murs végétalisés",
                "description": "Installer des toitures végétalisées ou des bardages isolants "
                               "sur les bâtiments exposés. Subventionnable via MaPrimeRénov'.",
                "impact": "−30% de chaleur en été",
                "priority": "haute" if jours_chauds > 30 else "moyenne",
                "source": "ADEME 2024",
            },
            {
                "titre": "Plans canicule locaux",
                "description": "Créer ou renforcer le plan canicule communal : identifier "
                               "les personnes vulnérables, ouvrir des espaces de fraîcheur.",
                "impact": "Réduction de la mortalité caniculaire",
                "priority": "haute",
                "source": "Santé Publique France",
            },
            {
                "titre": "Comportements individuels",
                "description": "Fermer les volets le jour, hydratation fréquente, "
                               "éviter les sorties entre 12h-16h en période de canicule.",
                "impact": "Prévention des coups de chaleur",
                "priority": "moyenne",
                "source": "Ministère de la Santé",
            },
            {
                "titre": "Îlots de fraîcheur urbain",
                "description": f"Cartographier et développer les zones fraîches dans {territoire} : "
                               "fontaines, parcs, bâtiments publics climatisés identifiés.",
                "impact": "Accès refuge pour les populations vulnérables",
                "priority": "haute",
                "source": "Earth Action Report 2025",
            },
        ]
        return recs

    # 
    # SÉCHERESSE
    # 
    def _recs_secheresse(self, deficit: float) -> List[Dict]:
        return [
            {
                "titre": "Récupération d'eau de pluie",
                "description": "Installer des cuves de récupération (500L à 10 000L). "
                               "Utilisable pour arrosage, toilettes. Subventionné par certaines communes.",
                "impact": "−30 à −50% de consommation d'eau extérieure",
                "priority": "haute" if deficit < -20 else "moyenne",
                "source": "Agences de l'eau",
            },
            {
                "titre": "Plantes résistantes à la sécheresse",
                "description": "Favoriser les espèces méditerranéennes (lavande, romarin, "
                               "graminées) et le paillage pour limiter l'évaporation.",
                "impact": "−70% d'arrosage nécessaire",
                "priority": "moyenne",
                "source": "INRAE — Guide jardinage climatique",
            },
            {
                "titre": "Restrictions d'arrosage anticipées",
                "description": "Adopter des plans de sobriété hydrique estivaux dès le printemps "
                               "pour anticiper les épisodes de sécheresse intense.",
                "impact": "Préservation des nappes phréatiques",
                "priority": "haute",
                "source": "PNACC 3 · Axe 2",
            },
            {
                "titre": "Agriculture adaptée",
                "description": "Développer les cultures adaptées au climat futur : "
                               "espèces résistantes, agroforesterie, irrigation efficiente (goutte-à-goutte).",
                "impact": "Maintien de la sécurité alimentaire",
                "priority": "haute",
                "source": "Ministère de l'Agriculture 2025",
            },
        ]

    # 
    # FEUX DE FORÊT
    # 
    def _recs_feux(self) -> List[Dict]:
        return [
            {
                "titre": "Débroussaillage obligatoire",
                "description": "Respecter l'obligation légale de débroussaillage à 50m des habitations "
                               "(jusqu'à 200m en zone à risque). Vérifier arrêté préfectoral.",
                "impact": "Réduction du risque de propagation de 60%",
                "priority": "haute",
                "source": "Code forestier Art. L131-10",
            },
            {
                "titre": "Aménagement anti-incendie",
                "description": "Créer des coupures de combustible, maintenir des pare-feux "
                               "et des accès pompiers dégagés autour des zones habitées.",
                "impact": "Protection des habitations et évacuation facilitée",
                "priority": "haute",
                "source": "SDIS — Plan de Prévention des Risques",
            },
            {
                "titre": "Procédures d'urgence connues",
                "description": "Connaître le numéro 18, le plan d'évacuation local, "
                               "et les points de rassemblement. Préparer un kit d'urgence.",
                "impact": "Réduction de la mortalité en cas d'incendie",
                "priority": "haute",
                "source": "Sécurité civile France",
            },
        ]

    # 
    # RÉDUCTION CARBONE
    # 
    def _recs_carbone(self) -> List[Dict]:
        return [
            {
                "titre": "Mobilité douce et transports décarbonés",
                "description": "Adopter le vélo, les transports en commun ou le covoiturage. "
                               "Le transport représente ~30% de l'empreinte carbone individuelle.",
                "impact": "−1.5 tCO₂eq/an (remplacement voiture thermique)",
                "priority": "haute",
                "source": "ADEME — Bilan carbone individuel 2024",
            },
            {
                "titre": "Alimentation bas carbone",
                "description": "Réduire la consommation de viande rouge (surtout bœuf), "
                               "favoriser les produits locaux et de saison. "
                               "L'alimentation = ~25% de l'empreinte.",
                "impact": "−1 tCO₂eq/an (régime flexitarien)",
                "priority": "haute",
                "source": "ADEME — Impact alimentation 2024",
            },
            {
                "titre": "Rénovation énergétique",
                "description": "Isoler les combles, changer la chaudière pour une pompe à chaleur. "
                               "MaPrimeRénov' couvre jusqu'à 90% pour ménages modestes.",
                "impact": "−2 à −3 tCO₂eq/an + économies facture",
                "priority": "haute",
                "source": "PNACC 3 · Plan Rénovation 2030",
            },
            {
                "titre": "Consommation responsable",
                "description": "Allonger la durée de vie des équipements, réparer plutôt que remplacer, "
                               "acheter d'occasion. Les biens manufacturés = ~20% de l'empreinte.",
                "impact": "−0.5 à −1 tCO₂eq/an",
                "priority": "moyenne",
                "source": "Earth Action Report 2025",
            },
        ]

    # 
    # ADAPTATION TERRITORIALE
    # 
    def _recs_adaptation(self, territoire: str) -> List[Dict]:
        return [
            {
                "titre": f"Plan Climat Air Énergie Territorial (PCAET) de {territoire}",
                "description": "S'informer et participer à l'élaboration du PCAET local. "
                               "Ce plan définit les objectifs de réduction des émissions à l'échelle du territoire.",
                "impact": "Mobilisation collective de la collectivité",
                "priority": "moyenne",
                "source": "PNACC 3 — Gouvernance territoriale",
            },
            {
                "titre": "Infrastructure résiliente",
                "description": "Anticiper la mise en conformité des réseaux (eau, énergie) "
                               "aux événements climatiques extrêmes. Audit de vulnérabilité recommandé.",
                "impact": "Réduction des coûts des catastrophes climatiques",
                "priority": "haute",
                "source": "Caisse Centrale de Réassurance 2024",
            },
            {
                "titre": "Sensibilisation et éducation",
                "description": "Organiser des ateliers de sensibilisation, intégrer "
                               "l'éducation climatique dans les établissements scolaires.",
                "impact": "Multiplication des comportements engagés",
                "priority": "moyenne",
                "source": "Earth Action Report 2025",
            },
        ]


if __name__ == "__main__":
    engine = RecommendationEngine()
    recs = engine.get_recommendations(
        risk_score=75, jours_chauds=30, deficit_precip=-15, territoire="Paris"
    )
    for cat, actions in recs.items():
        print(f"\n{cat}")
        for a in actions:
            print(f"  [{a['priority'].upper()}] {a['titre']}")
