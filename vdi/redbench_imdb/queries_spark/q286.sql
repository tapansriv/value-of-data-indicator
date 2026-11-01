SELECT
  COUNT(*)
FROM name AS n, aka_name AS an, info_type AS it1, person_info AS pi1, cast_info AS ci, role_type AS rt
WHERE
  n.id = ci.person_id
  AND ci.person_id = pi1.person_id
  AND it1.id = pi1.info_type_id
  AND n.id = pi1.person_id
  AND n.id = an.person_id
  AND ci.person_id = an.person_id
  AND an.person_id = pi1.person_id
  AND rt.id = ci.role_id
  AND (
    n.gender IN ('m')
  )
  AND (
    n.name_pcode_nf IN ('C6361', 'F6524', 'G5125', 'J2323', 'J6134', 'R1563', 'R1632', 'S2351', 'W3134')
  )
  AND (
    ci.note IN ('(executive producer: FUNimation Entertainment)', '(head writer)', '(uncredited)', '(voice)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'producer', 'writer')
  )
  AND (
    it1.id IN ('34')
  )
