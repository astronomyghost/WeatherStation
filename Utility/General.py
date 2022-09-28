def sqliteTupleToList(list, j):
    rfList = []  # Queries from the sql database are received as tuples so it must be refined to an ordinary list
    for i in range(len(list)):
        rfList.append(list[i][j])
    return rfList