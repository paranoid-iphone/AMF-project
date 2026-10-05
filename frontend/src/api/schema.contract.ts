import type { components } from "./schema";

type Assert<T extends true> = T;
type EmptyRecord = Record<never, never>;
type IsOptional<T, K extends keyof T> = EmptyRecord extends Pick<T, K> ? true : false;
type OptionalKeys<T> = {
  [K in keyof T]-?: EmptyRecord extends Pick<T, K> ? K : never;
}[keyof T];
type Equal<Left, Right> = (<T>() => T extends Left ? 1 : 2) extends <T>() =>
  T extends Right ? 1 : 2
  ? true
  : false;

type CreateRequest = components["schemas"]["ProjectWriteRequest"];
type PatchRequest = components["schemas"]["PatchedProjectWriteRequest"];

export type CreateCurrencyIsOptional = Assert<IsOptional<CreateRequest, "currency">>;
export type CreateTitleIsRequired = Assert<
  Equal<IsOptional<CreateRequest, "title">, false>
>;
export type PatchFieldsAreAllOptional = Assert<Equal<OptionalKeys<PatchRequest>, keyof PatchRequest>>;
