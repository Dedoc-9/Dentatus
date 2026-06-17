# commit_exp312.ps1 -- EXP-312 commit (run from PowerShell in Reality_Engine dir)
# Protocol: exp312-v1
# declaration_hash: 2e6ccdc20da7aefb2a6bb3b024d8a3102c87e706d610ba454122afaf66329cc5

Set-Location $PSScriptRoot

git add engine/operators.py
git add run_seed_exp312.py
git add run_p_invariance_exp312.py
git add studies/exp312_symmetric_budget/SEED_DECLARATION_exp312.json
git add studies/exp312_symmetric_budget/ENGINE_AXIOMS_exp312.md

git commit -m "EXP-312: The Symmetric Budget -- close P_yz Asymmetry Debt

declaration_hash: 2e6ccdc20da7aefb2a6bb3b024d8a3102c87e706d610ba454122afaf66329cc5

Two fixes for full multi-step P_yz invariance:
  Fix 1: _bbox_hash_payload_312 -- extents-based payload f(|hi-lo|),
          coordinate-free, replaces absolute-coord _bbox_hash_payload
  Fix 2: uniform Sector A split -- stalk_A_i = stalk_A / N for all i
          replaces index-based orthogonal decompose which coupled octant
          index ordering to spatial position (permuted under P_yz: i <-> i XOR 4)

Root causes closed:
  Source 1 (EXP-311 known): K_bound/payload encoded absolute x-coords
  Source 2 (EXP-312 new):   _orthogonal_decompose mass by index != by spatial pos

Result: fwd_leaves == mir_leaves == 36 (was 92 vs 99 in EXP-311)
        cost_fwd == cost_mir (delta=7.99e-15)
        norm(S_C), norm(S_A) exactly P_yz-invariant at all depths

Fork A (run_seed_exp312.py):         8/8 PASS
Fork B (run_p_invariance_exp312.py): 10/10 PASS

Dev note: uniform Sector A split conserves sum (N*(stalk_A/N)=stalk_A),
makes mass-weighted centroid = geometric centroid, which is exactly
P_yz-covariant. LOD values identical across all depths => identical
recursion tree. Gravitational backreaction: the ghost EMA (S_A, S_C)
is now a fully symmetric observable under spatial reflection.

EXP-313 gate: series-300 closed. EXP-401 requires stalk schema extension
to d=15 or d=18 with Gaussian covariance dims for anisotropic splatting."

git push
