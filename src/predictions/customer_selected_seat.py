import pyidaungsu as pds

def customer_selected_seat_plan(input, avaliables_seat):
    if not avaliables_seat:
        return 0
    new_tokens = pds.tokenize(input)
    for token in new_tokens:
        if token in avaliables_seat:
            return 1
    return 0
