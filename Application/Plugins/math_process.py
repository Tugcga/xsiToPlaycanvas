def xsi_matrix_to_matrix(xsi_matrix):
    return [[xsi_matrix.Value(i, j) for j in range(4)] for i in range(4)]


def apply_matrix(matrix, value):
    to_return = [0] * 4
    for i in range(4):
        s = 0.0
        for j in range(4):
            s += value[j] * matrix[j][i]
        to_return[i] = s
    return tuple(to_return)
