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
    n.gender IN ('f')
  )
  AND (
    n.name_pcode_nf IN ('A164', 'A3434', 'A53', 'A5431', 'B14', 'B3524', 'B563', 'C4152', 'C6431', 'C6534', 'F3626', 'P1261', 'R1423', 'R1546', 'R3165', 'S1353', 'S3251')
  )
  AND (
    ci.note IN ('(as Ann Todd)', '(as Bethany Joy Galeotti)', '(as Phebe Khae Arbotante)', '(uncredited)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'costume designer', 'director', 'writer')
  )
  AND (
    it1.id IN ('25')
  )
