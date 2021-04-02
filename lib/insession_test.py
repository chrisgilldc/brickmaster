#!/usr/bin/python3

# Tester for Insession.

from insession import insession

insession = insession()
print("Testing House status...")
print(insession.status('house'))
print("Testing Senate status...")
print(insession.status('senate'))

print("Next House meeting...")
print(insession.next('house'))
print("Next Senate meeting...")
print(insession.next('senate'))
#testtime = datetime.strptime('20210329T1035','%Y%m%dT%H%M')
#print(insession.next('house'))
