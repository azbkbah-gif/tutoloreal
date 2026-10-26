from src.modeles.mission import Mission, Consultant

if __name__ == "__main__":
    # On crée deux objets Mission
    m1 = Mission("L'Oréal", 600, 150)
    m2 = Mission("Carrefour", 540, 40)

    print(m1)                     # appelle __repr__
    print(m1.ca())                # appelle la méthode ca
    print(m1.ca_annuel(20))       # 600 x 20 x 11

    # Un objet Consultant qui contient une liste de missions
    aziz = Consultant("Aziz Bah", [m1, m2])
    print(aziz)
    print(aziz.ca_total())
    print(aziz.meilleure_mission())